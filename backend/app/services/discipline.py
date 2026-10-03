"""Calcul disciplinaire dérivé des événements validés.

Aucune valeur disciplinaire n'est appliquée si le règlement de l'édition ne
la fournit pas. Les événements historiques restent inchangés.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StatutMatch, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.sport_engine import ReglementVersion, SanctionDisciplinaire
from app.schemas.sport_engine import DisciplineReglement
from app.services.reglements import get_reglement_pour_match


def _value(value):
    return value.value if hasattr(value, "value") else value


def _not_refused():
    return or_(EvenementMatch.refuse.is_(False), EvenementMatch.refuse.is_(None))


async def _match(db: AsyncSession, match_id: int) -> Match:
    row = await db.get(Match, match_id)
    if row is None:
        raise ValueError("Match introuvable")
    return row


async def _events_before(db: AsyncSession, saison_id: int, joueur_id: int, current: Match):
    query = (
        select(EvenementMatch, Match)
        .join(Match, Match.id == EvenementMatch.match_id)
        .where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
            EvenementMatch.joueur_id == joueur_id,
            EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
            _not_refused(),
            or_(
                Match.date_heure < current.date_heure,
                and_(Match.date_heure == current.date_heure, Match.id < current.id),
            ),
            EvenementMatch.type.in_([TypeEvenement.CARTON_JAUNE, TypeEvenement.CARTON_ROUGE]),
        )
        .order_by(Match.date_heure, Match.id, EvenementMatch.id)
    )
    return list((await db.execute(query)).all())


def _club_for_event(match: Match, event: EvenementMatch) -> int | None:
    side = _value(event.equipe_concernee)
    return match.equipe_domicile_id if side == "domicile" else match.equipe_exterieur_id


async def _club_matches_after_trigger(
    db: AsyncSession, club_id: int | None, trigger: Match, current: Match
) -> int:
    if club_id is None:
        return 0
    result = await db.execute(
        select(Match.id).where(
            Match.saison_id == current.saison_id,
            Match.statut == StatutMatch.VALIDE,
            or_(Match.equipe_domicile_id == club_id, Match.equipe_exterieur_id == club_id),
            or_(
                Match.date_heure > trigger.date_heure,
                and_(Match.date_heure == trigger.date_heure, Match.id > trigger.id),
            ),
            or_(
                Match.date_heure < current.date_heure,
                and_(Match.date_heure == current.date_heure, Match.id < current.id),
            ),
        )
    )
    return len(result.scalars().all())


async def get_discipline_summary(
    db: AsyncSession,
    joueur_id: int,
    current_match: Match,
    reglement: ReglementVersion | None,
) -> dict:
    events = await _events_before(db, current_match.saison_id, joueur_id, current_match)
    jaunes = [(event, match) for event, match in events if _value(event.type) == "carton_jaune"]
    rouges = [(event, match) for event, match in events if _value(event.type) == "carton_rouge"]
    result = {
        "joueur_id": joueur_id,
        "saison_id": current_match.saison_id,
        "reglement_version_id": reglement.id if reglement else None,
        "jaunes_valides": len(jaunes),
        "rouges_valides": len(rouges),
        "sanctions": [],
        "statut": "OK",
        "message": "Aucune indisponibilité disciplinaire calculée.",
        "sources": [
            {"type": "evenement", "id": event.id, "match_id": match.id, "fait": _value(event.type)}
            for event, match in events
        ],
    }
    if reglement is None:
        result.update(
            statut="ATTENTION",
            message="Aucun règlement n'est rattaché à ce match : la discipline n'est pas calculée automatiquement.",
        )
        return result
    try:
        discipline = DisciplineReglement.model_validate((reglement.configuration or {}).get("discipline"))
    except Exception:
        result.update(statut="ATTENTION", message="La configuration disciplinaire du règlement est incomplète.")
        return result
    if not discipline.model_dump(exclude_none=True):
        result.update(statut="ATTENTION", message="Aucune règle disciplinaire n'est configurée pour cette édition.")
        return result

    candidates: list[dict] = []
    # Rouge direct ou rouge dérivé du deuxième jaune. On privilégie la règle
    # explicitement dédiée au deuxième jaune pour éviter le double comptage.
    for event, match in rouges:
        derived = _value(event.source) == "deuxieme_jaune"
        duration = discipline.suspension_apres_deuxieme_jaune if derived else discipline.suspension_apres_rouge
        if duration is None:
            continue
        served = await _club_matches_after_trigger(
            db, _club_for_event(match, event), match, current_match
        )
        if served < duration:
            candidates.append(
                {
                    "type": "deuxieme_jaune" if derived else "rouge",
                    "duree": duration,
                    "restants": duration - served,
                    "match_id": match.id,
                    "evenement_id": event.id,
                    "message": (
                        "Joueur suspendu — deuxième jaune"
                        if derived
                        else "Joueur suspendu — carton rouge"
                    ),
                }
            )

    threshold = discipline.jaunes_pour_suspension
    duration = discipline.duree_accumulation
    if threshold and duration and jaunes:
        # Un seuil est évalué par franchissement (2, 4, 6...) afin de ne pas
        # recréer une sanction à chaque match après le premier seuil.
        crossings = len(jaunes) // threshold
        for index in range(crossings):
            event, match = jaunes[(index + 1) * threshold - 1]
            # Un rouge issu du deuxième jaune porte déjà la sanction de ce
            # match si la configuration le prévoit : on évite le doublon.
            if any(candidate["match_id"] == match.id and candidate["type"] == "deuxieme_jaune" for candidate in candidates):
                continue
            served = await _club_matches_after_trigger(
                db, _club_for_event(match, event), match, current_match
            )
            if served < duration:
                candidates.append(
                    {
                        "type": "accumulation_jaunes",
                        "duree": duration,
                        "restants": duration - served,
                        "match_id": match.id,
                        "evenement_id": event.id,
                        "message": "Joueur suspendu — accumulation de cartons jaunes",
                    }
                )

    # Une décision du Comité s'applique à la proposition de sanction
    # correspondante sans réécrire les cartons source. Les sanctions simples
    # non confirmées restent calculées à la volée.
    if candidates:
        trigger_ids = [candidate["evenement_id"] for candidate in candidates]
        persisted_rows = (
            await db.execute(
                select(SanctionDisciplinaire).where(
                    SanctionDisciplinaire.joueur_id == joueur_id,
                    SanctionDisciplinaire.saison_id == current_match.saison_id,
                    SanctionDisciplinaire.evenement_declencheur_id.in_(trigger_ids),
                )
            )
        ).scalars().all()
        persisted_by_event = {row.evenement_declencheur_id: row for row in persisted_rows}
        adjusted = []
        for candidate in candidates:
            sanction = persisted_by_event.get(candidate["evenement_id"])
            if sanction is not None and sanction.statut == "annulee":
                continue
            if sanction is not None and sanction.statut in {"confirmee", "modifiee"}:
                if sanction.matchs_restants <= 0:
                    continue
                candidate = {**candidate, "restants": sanction.matchs_restants, "duree": sanction.nombre_matchs}
            adjusted.append(candidate)
        candidates = adjusted

    if candidates:
        # Une seule indisponibilité est suffisante pour bloquer ; toutes les
        # sources restent exposées pour l'audit et l'explication.
        result["statut"] = "BLOQUANT"
        result["sanctions"] = candidates
        result["message"] = candidates[0]["message"] + f" — {candidates[0]['restants']} match(s) restant(s)."
    elif threshold and len(jaunes) + 1 == threshold:
        result["statut"] = "ATTENTION"
        result["message"] = "Joueur proche du seuil de suspension disciplinaire."
    return result


async def persist_calculated_sanctions(
    db: AsyncSession, joueur_id: int, current_match: Match, reglement: ReglementVersion
) -> list[SanctionDisciplinaire]:
    """Persiste les propositions calculées sans toucher aux matchs historiques."""
    summary = await get_discipline_summary(db, joueur_id, current_match, reglement)
    created: list[SanctionDisciplinaire] = []
    for item in summary["sanctions"]:
        source = f"{joueur_id}:{current_match.saison_id}:{item['type']}:{item['evenement_id']}"
        fingerprint = hashlib.sha256(source.encode()).hexdigest()
        existing = await db.scalar(
            select(SanctionDisciplinaire).where(
                SanctionDisciplinaire.joueur_id == joueur_id,
                SanctionDisciplinaire.saison_id == current_match.saison_id,
                SanctionDisciplinaire.empreinte_source == fingerprint,
            )
        )
        if existing is not None:
            continue
        row = SanctionDisciplinaire(
            competition_id=reglement.competition_id,
            saison_id=current_match.saison_id,
            joueur_id=joueur_id,
            reglement_version_id=reglement.id,
            evenement_declencheur_id=item["evenement_id"],
            type_motif=item["type"],
            statut=("calculee" if (reglement.configuration or {}).get("discipline", {}).get("mode_decision") == "automatique" else "a_confirmer"),
            nombre_matchs=item["duree"],
            matchs_restants=item["restants"],
            explication=item["message"],
            configuration_snapshot=(reglement.configuration or {}).get("discipline"),
            empreinte_source=fingerprint,
        )
        db.add(row)
        created.append(row)
    return created
