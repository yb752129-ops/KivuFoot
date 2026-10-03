"""Checklist sportive additive avant validation officielle."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import SaisonClub
from app.models.enums import (
    EquipeConcernee,
    StatutMatch,
    StatutParticipation,
    StatutValidationEvenement,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.match import Match, MatchParticipation
from app.models.sport_engine import ControleValidationMatch, ReglementVersion
from app.schemas.sport_engine import ChecklistOut, ControleOut
from app.services.discipline import get_discipline_summary
from app.services.eligibilite import verifier_joueur
from app.services.reglements import get_reglement_pour_match


def _value(value):
    return value.value if hasattr(value, "value") else value


def _not_refused():
    return or_(EvenementMatch.refuse.is_(False), EvenementMatch.refuse.is_(None))


def _control(code: str, libelle: str, statut: str, message: str, *sources: dict) -> ControleOut:
    return ControleOut(code=code, libelle=libelle, statut=statut, message=message, sources=list(sources))


def _max_status(values: list[str]) -> str:
    if "BLOQUANT" in values:
        return "BLOQUANT"
    if "ATTENTION" in values:
        return "ATTENTION"
    return "OK"


async def _events(db: AsyncSession, match_id: int):
    return list(
        (
            await db.execute(
                select(EvenementMatch).where(EvenementMatch.match_id == match_id)
            )
        ).scalars().all()
    )


async def _score_from_events(events: list[EvenementMatch]) -> tuple[int, int, list[EvenementMatch]]:
    dom = ext = 0
    scorants = []
    for event in events:
        if event.statut_validation != StatutValidationEvenement.VALIDE or event.refuse:
            continue
        if not event.score_comptabilise:
            continue
        type_event = _value(event.type)
        marked = type_event == "but" or (
            type_event == "penalty" and _value(event.resultat) == "marque"
        )
        if type_event == "but_contre_son_camp":
            marked = True
            side = "exterieur" if _value(event.equipe_concernee) == "domicile" else "domicile"
        else:
            side = _value(event.equipe_concernee)
        if not marked:
            continue
        scorants.append(event)
        if side == "domicile":
            dom += 1
        else:
            ext += 1
    return dom, ext, scorants


async def run_checklist(db: AsyncSession, match: Match) -> ChecklistOut:
    reglement = await get_reglement_pour_match(db, match, allow_active_for_new=True)
    config = reglement.configuration if reglement else {}
    mode = config.get("mode_moteur", "legacy") if isinstance(config, dict) else "legacy"
    controls: list[ControleOut] = []

    statut_match = _value(match.statut)
    controls.append(
        _control(
            "match_termine",
            "Match terminé",
            "OK" if statut_match in {StatutMatch.TERMINE.value, StatutMatch.VALIDE.value} else "BLOQUANT",
            "Le match est terminé." if statut_match in {StatutMatch.TERMINE.value, StatutMatch.VALIDE.value} else "Le match doit être terminé avant validation.",
        )
    )

    events = await _events(db, match.id)
    pending = [e for e in events if _value(e.statut_validation) == StatutValidationEvenement.EN_ATTENTE.value]
    controls.append(
        _control(
            "evenements_traites",
            "Tous les événements traités",
            "OK" if not pending else "BLOQUANT",
            "Aucun événement en attente." if not pending else f"{len(pending)} événement(s) attendent une décision.",
            *({"type": "evenement", "id": e.id} for e in pending),
        )
    )

    clubs = (
        await db.execute(
            select(SaisonClub.club_id).where(
                SaisonClub.saison_id == match.saison_id,
                SaisonClub.club_id.in_([match.equipe_domicile_id, match.equipe_exterieur_id]),
            )
        )
    ).scalars().all()
    teams_ok = match.equipe_domicile_id is not None and match.equipe_exterieur_id is not None and len(set(clubs)) == 2
    controls.append(
        _control(
            "equipes_inscrites",
            "Équipes inscrites",
            "OK" if teams_ok else "BLOQUANT",
            "Les deux équipes sont inscrites à la saison." if teams_ok else "Une ou deux équipes ne sont pas inscrites à cette saison.",
        )
    )

    if reglement is None:
        controls.append(
            _control(
                "reglement_rattache",
                "Règlement de l'édition",
                "ATTENTION",
                "Aucun règlement actif n'est rattaché : les contrôles spécifiques ne sont pas appliqués automatiquement.",
            )
        )
    else:
        controls.append(
            _control(
                "reglement_rattache",
                "Règlement de l'édition",
                "OK",
                f"Règlement version {reglement.version} utilisé.",
                {"type": "reglement", "id": reglement.id},
            )
        )

    expected_dom, expected_ext, scorants = await _score_from_events(events)
    if match.resultat_retroactif:
        controls.append(
            _control(
                "score_coherent",
                "Score cohérent",
                "OK",
                "Résultat rétroactif : le score officiel est porté par la décision et sa note, sans fabriquer de buteurs.",
            )
        )
    else:
        score_ok = expected_dom == match.score_domicile and expected_ext == match.score_exterieur
        score_status = "OK" if score_ok else ("ATTENTION" if match.locked else "BLOQUANT")
        controls.append(
            _control(
                "score_coherent",
                "Score cohérent",
                score_status,
                (
                    "Le score correspond aux événements comptabilisés."
                    if score_ok
                    else f"Score saisi {match.score_domicile}-{match.score_exterieur}, événements comptabilisés {expected_dom}-{expected_ext}."
                ),
            )
        )

    missing_scorers = [e for e in scorants if e.joueur_id is None]
    scorer_status = "OK" if not missing_scorers else ("ATTENTION" if match.locked else "BLOQUANT")
    controls.append(
        _control(
            "buteurs_coherents",
            "Buteurs cohérents",
            scorer_status,
            "Les événements comptabilisés ont un joueur associé." if not missing_scorers else "Un ou plusieurs buts comptabilisés n'ont pas de joueur associé.",
            *({"type": "evenement", "id": e.id} for e in missing_scorers),
        )
    )

    missing_passers = [
        e for e in events
        if _value(e.type) == TypeEvenement.BUT.value
        and e.statut_validation == StatutValidationEvenement.VALIDE
        and not e.refuse
        and e.joueur_secondaire_id is None
    ]
    # Le passeur est optionnel dans le modèle actuel : ATTENTION seulement.
    controls.append(
        _control(
            "passeurs_coherents",
            "Passeurs renseignés lorsque disponibles",
            "ATTENTION" if missing_passers and scorants else "OK",
            "Le passeur reste optionnel pour les buts sans passe décisive renseignée."
            if missing_passers and scorants
            else "Aucune incohérence de passeur détectée.",
        )
    )

    participations = list(
        (
            await db.execute(
                select(MatchParticipation).where(MatchParticipation.match_id == match.id)
            )
        ).scalars().all()
    )
    by_side = {
        "domicile": [p for p in participations if _value(p.equipe_concernee) == "domicile"],
        "exterieur": [p for p in participations if _value(p.equipe_concernee) == "exterieur"],
    }
    composition_rule = (config or {}).get("composition") if isinstance(config, dict) else None
    if composition_rule:
        for side, label in (("domicile", "Équipe domicile"), ("exterieur", "Équipe extérieur")):
            rows = by_side[side]
            titulaires = sum(_value(p.statut) == StatutParticipation.TITULAIRE.value for p in rows)
            banc = sum(_value(p.statut) == StatutParticipation.REMPLACANT.value for p in rows)
            tmin = composition_rule.get("titulaires_min")
            tmax = composition_rule.get("titulaires_max")
            bmin = composition_rule.get("remplacants_min")
            bmax = composition_rule.get("remplacants_max")
            bad = []
            if tmin is not None and titulaires < tmin:
                bad.append(f"{titulaires} titulaire(s), minimum {tmin}")
            if tmax is not None and titulaires > tmax:
                bad.append(f"{titulaires} titulaire(s), maximum {tmax}")
            if bmin is not None and banc < bmin:
                bad.append(f"{banc} remplaçant(s), minimum {bmin}")
            if bmax is not None and banc > bmax:
                bad.append(f"{banc} remplaçant(s), maximum {bmax}")
            controls.append(
                _control(
                    f"composition_{side}",
                    f"Composition conforme — {label}",
                    "BLOQUANT" if bad else "OK",
                    "; ".join(bad) if bad else f"{titulaires} titulaire(s), {banc} remplaçant(s).",
                )
            )
    else:
        controls.append(
            _control(
                "composition_regle",
                "Règle de composition",
                "ATTENTION",
                "Aucune limite officielle de composition n'est configurée pour ce règlement.",
            )
        )

    if not participations:
        controls.append(
            _control(
                "composition_complete",
                "Composition présente",
                "ATTENTION" if match.locked else "BLOQUANT",
                "Aucune participation n'est enregistrée pour ce match.",
            )
        )
    else:
        controls.append(_control("composition_complete", "Composition présente", "OK", "Des participations sont enregistrées."))

    eligibility_controls: list[ControleOut] = []
    for participation in participations:
        club_id = participation.club_id
        result = await verifier_joueur(db, match, participation.joueur_id, club_id, equipe=_value(participation.equipe_concernee))
        if result.statut == "BLOQUANT":
            eligibility_controls.append(
                _control(
                    "joueur_eligible",
                    "Joueurs éligibles",
                    "BLOQUANT",
                    result.message,
                    {"joueur_id": result.joueur_id, "code": result.code, "sources": result.sources},
                )
            )
        elif result.statut == "ATTENTION":
            eligibility_controls.append(
                _control(
                    "joueur_eligible",
                    "Joueurs éligibles",
                    "ATTENTION",
                    result.message,
                    {"joueur_id": result.joueur_id, "code": result.code, "sources": result.sources},
                )
            )
    if eligibility_controls:
        controls.extend(eligibility_controls)
    else:
        controls.append(_control("joueur_eligible", "Joueurs éligibles", "OK", "Aucune indisponibilité détectée."))

    replacements = [
        e for e in events
        if _value(e.type) == TypeEvenement.REMPLACEMENT
        and e.statut_validation == StatutValidationEvenement.VALIDE
        and not e.refuse
    ]
    replacement_rule = (config or {}).get("composition", {}) if isinstance(config, dict) else {}
    max_changes = replacement_rule.get("changements_max") if isinstance(replacement_rule, dict) else None
    if max_changes is not None and len(replacements) > max_changes:
        replacement_status = "BLOQUANT"
        replacement_message = f"{len(replacements)} changements enregistrés, maximum {max_changes}."
    else:
        replacement_status = "OK" if max_changes is not None else "ATTENTION"
        replacement_message = (
            f"{len(replacements)} changement(s), limite {max_changes}."
            if max_changes is not None
            else "Aucune limite officielle de changements n'est configurée."
        )
    controls.append(_control("remplacements_coherents", "Remplacements cohérents", replacement_status, replacement_message))

    # Les cartons sont déjà validés par le workflow événementiel ; la
    # discipline détaillée est exposée par le service d'éligibilité.
    pending_cards = [
        e for e in events
        if _value(e.type) in (TypeEvenement.CARTON_JAUNE.value, TypeEvenement.CARTON_ROUGE.value)
        and _value(e.statut_validation) == StatutValidationEvenement.EN_ATTENTE.value
    ]
    controls.append(
        _control(
            "cartons_coherents",
            "Cartons cohérents",
            "BLOQUANT" if pending_cards else "OK",
            "Aucun carton en attente." if not pending_cards else f"{len(pending_cards)} carton(s) en attente de validation.",
        )
    )

    mandatory_ok = match.date_heure is not None and match.equipe_domicile_id is not None and match.equipe_exterieur_id is not None
    controls.append(
        _control(
            "donnees_obligatoires",
            "Données obligatoires complètes",
            "OK" if mandatory_ok else "BLOQUANT",
            "Date, stade logique et équipes présents." if mandatory_ok else "Date ou équipe manquante.",
        )
    )

    # En LEGACY/REPORT_ONLY, les contrôles sportifs restent visibles mais ne
    # deviennent pas des blocages de validation. Les contrôles structurels
    # existants restent bloquants.
    effective_statuses = []
    for control in controls:
        if control.statut == "BLOQUANT" and mode != "enforced" and control.code not in {
            "match_termine",
            "evenements_traites",
            "equipes_inscrites",
            "donnees_obligatoires",
        }:
            effective_statuses.append("ATTENTION")
        else:
            effective_statuses.append(control.statut)
    resultat = _max_status(effective_statuses)
    return ChecklistOut(
        match_id=match.id,
        resultat=resultat,
        mode=mode,
        reglement_version_id=reglement.id if reglement else None,
        controles=controls,
        generated_at=datetime.now(timezone.utc),
    )


async def save_checklist(
    db: AsyncSession, match: Match, checklist: ChecklistOut, user_id: int
) -> ControleValidationMatch:
    payload = checklist.model_dump(mode="json")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    row = ControleValidationMatch(
        match_id=match.id,
        reglement_version_id=checklist.reglement_version_id,
        resultat=checklist.resultat,
        empreinte_source=hashlib.sha256(canonical.encode()).hexdigest(),
        controles=payload,
        execute_par_id=user_id,
    )
    db.add(row)
    await db.flush()
    return row


def bloquants_effectifs(checklist: ChecklistOut) -> list[ControleOut]:
    if checklist.mode != "enforced":
        return [
            control
            for control in checklist.controles
            if control.statut == "BLOQUANT"
            and control.code in {"match_termine", "evenements_traites", "equipes_inscrites", "donnees_obligatoires"}
        ]
    return [control for control in checklist.controles if control.statut == "BLOQUANT"]
