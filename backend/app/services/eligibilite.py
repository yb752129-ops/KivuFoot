"""Contrôle centralisé de l'éligibilité d'un joueur pour un match."""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StatutJoueur
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.sport_engine import DecisionSportive, EffectifVersion, EffectifVersionJoueur
from app.schemas.sport_engine import EligibiliteOut
from app.services.discipline import get_discipline_summary
from app.services.reglements import get_reglement_pour_match


def _value(value):
    return value.value if hasattr(value, "value") else value


async def _active_effectif(db: AsyncSession, saison_id: int, club_id: int) -> EffectifVersion | None:
    result = await db.execute(
        select(EffectifVersion)
        .where(
            EffectifVersion.saison_id == saison_id,
            EffectifVersion.club_id == club_id,
            EffectifVersion.statut == "valide",
        )
        .order_by(EffectifVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _override(db: AsyncSession, match_id: int, joueur_id: int) -> DecisionSportive | None:
    result = await db.execute(
        select(DecisionSportive)
        .where(
            DecisionSportive.match_id == match_id,
            DecisionSportive.joueur_id == joueur_id,
            DecisionSportive.type_decision == "eligibilite",
            DecisionSportive.action == "autoriser_participation",
            DecisionSportive.statut == "confirmee",
        )
        .order_by(DecisionSportive.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def verifier_joueur(
    db: AsyncSession,
    match: Match,
    joueur_id: int,
    club_id: int,
    *,
    equipe: str | None = None,
) -> EligibiliteOut:
    joueur = await db.get(Joueur, joueur_id)
    sources: list[dict] = []
    if joueur is None or joueur.anonymise or joueur.fusionne:
        return EligibiliteOut(
            joueur_id=joueur_id,
            statut="BLOQUANT",
            code="joueur_inconnu",
            message="Joueur introuvable ou identité fusionnée/anonymisée.",
        )

    reglement = await get_reglement_pour_match(db, match, allow_active_for_new=True)
    config = reglement.configuration if reglement else {}
    eligibilite_config = config.get("eligibilite", {}) if isinstance(config, dict) else {}
    require_effectif = bool(eligibilite_config.get("effectif_officiel_requis", False))
    statut = "OK"
    code = "eligible"
    message = "✅ Joueur éligible."

    if joueur.club_actuel_id != club_id:
        statut, code, message = "BLOQUANT", "club_incorrect", "🔴 Le joueur n'appartient pas à l'équipe concernée."
    elif _value(joueur.statut) != StatutJoueur.ACTIF.value:
        statut, code, message = "BLOQUANT", "joueur_inactif", f"🔴 Joueur indisponible — statut { _value(joueur.statut) }."
    else:
        effectif = await _active_effectif(db, match.saison_id, club_id)
        if effectif is None:
            statut, code, message = (
                ("BLOQUANT", "effectif_non_valide", "🔴 Effectif officiel non validé pour cette édition.")
                if require_effectif
                else ("ATTENTION", "effectif_non_rattache", "⚠️ Aucun instantané d'effectif officiel n'est rattaché à cette édition.")
            )
        else:
            membership = await db.scalar(
                select(EffectifVersionJoueur.id).where(
                    EffectifVersionJoueur.effectif_version_id == effectif.id,
                    EffectifVersionJoueur.joueur_id == joueur_id,
                )
            )
            if membership is None:
                statut, code, message = (
                    ("BLOQUANT", "hors_effectif", "🔴 Joueur non inscrit dans l'effectif officiel de cette édition.")
                    if require_effectif
                    else ("ATTENTION", "hors_effectif_historique", "⚠️ Joueur absent de l'instantané d'effectif disponible.")
                )
            else:
                sources.append({"type": "effectif", "id": effectif.id, "version": effectif.version})

    discipline = await get_discipline_summary(db, joueur_id, match, reglement)
    sources.extend(discipline.get("sources", []))
    if discipline["statut"] == "BLOQUANT":
        statut, code, message = "BLOQUANT", "suspendu", "🔴 " + discipline["message"]
    elif discipline["statut"] == "ATTENTION" and statut == "OK":
        statut, code, message = "ATTENTION", "discipline_non_configuree", "⚠️ " + discipline["message"]

    override = await _override(db, match.id, joueur_id)
    if override is not None and statut == "BLOQUANT":
        statut = "ATTENTION"
        code = "autorisation_comite"
        message = "⚠️ Participation exceptionnellement autorisée par le Comité d'Organisation."
        sources.append({"type": "decision_sportive", "id": override.id, "motif": override.motif})

    return EligibiliteOut(
        joueur_id=joueur.id,
        joueur_nom=joueur.nom_complet,
        club_id=club_id,
        statut=statut,
        code=code,
        message=message,
        sources=sources,
    )


async def verifier_liste_joueurs(
    db: AsyncSession, match: Match, joueur_ids: list[int], club_id: int, equipe: str | None = None
) -> list[EligibiliteOut]:
    return [await verifier_joueur(db, match, joueur_id, club_id, equipe=equipe) for joueur_id in joueur_ids]
