"""Règles versionnées de fin de match et de prolongation."""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.services.reglements import get_reglement_pour_match
from app.services.tirs_au_but import PHASES_ELIMINATOIRES

MODE_TIRS_APRES_90 = "tirs_au_but_apres_90"
MODE_PROLONGATIONS_2X15 = "prolongations_2x15"
MODES_EGALITE = {MODE_TIRS_APRES_90, MODE_PROLONGATIONS_2X15}
PERIODES_PROLONGATION = {"3", "mi_temps_et", "4"}


def _value(value):
    return value.value if hasattr(value, "value") else value


async def mode_egalite_eliminatoire(db: AsyncSession, match: Match) -> str:
    """Lit le règlement figé sur le match; les anciennes éditions gardent le mode historique."""
    reglement = await get_reglement_pour_match(db, match)
    configuration = reglement.configuration if reglement and isinstance(reglement.configuration, dict) else {}
    regle_match = configuration.get("match", {}) if isinstance(configuration, dict) else {}
    mode = regle_match.get("mode_egalite_eliminatoire") if isinstance(regle_match, dict) else None
    # Compatibilité des matchs historiques : avant cette configuration, les
    # tirs au but intervenaient directement après le temps réglementaire.
    return mode if mode in MODES_EGALITE else MODE_TIRS_APRES_90


def est_a_egalite(match: Match) -> bool:
    return int(match.score_domicile or 0) == int(match.score_exterieur or 0)


async def verifier_transition_periode(db: AsyncSession, match: Match, periode_demandee) -> None:
    """Valide l'enchaînement des périodes avant toute écriture."""
    demanded = _value(periode_demandee)
    current = _value(match.periode)
    if demanded == "mi_temps":
        if current not in (None, "1"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La mi-temps se siffle à la fin de la première période.")
        return
    if demanded == "2":
        if current != "mi_temps":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La deuxième période commence après la mi-temps.")
        return

    if demanded not in PERIODES_PROLONGATION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Période inconnue.")
    if _value(match.phase) not in PHASES_ELIMINATOIRES or match.forfait:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Les prolongations sont réservées aux matchs éliminatoires sans forfait.")
    mode = await mode_egalite_eliminatoire(db, match)
    if mode != MODE_PROLONGATIONS_2X15:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le règlement de cette compétition prévoit les tirs au but après 90 minutes, sans prolongations.")
    if demanded == "3":
        if current != "2" or not est_a_egalite(match):
            raise HTTPException(status.HTTP_409_CONFLICT, "Les prolongations commencent seulement après 90 minutes si le score est à égalité.")
        return
    if demanded == "mi_temps_et":
        if current != "3":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La mi-temps des prolongations suit la première période de prolongation.")
        return
    if demanded == "4":
        if current != "mi_temps_et":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La deuxième période de prolongation commence après sa mi-temps.")


async def verifier_fin_match(db: AsyncSession, match: Match) -> None:
    """Bloque la fin à 90 en cas d'égalité avec prolongations, et une fin prématurée."""
    if _value(match.phase) not in PHASES_ELIMINATOIRES or match.forfait:
        return
    current = _value(match.periode)
    if current in ("1", "mi_temps", "3", "mi_temps_et"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La période de jeu n'est pas terminée. Reprenez le match ou terminez les deux périodes de prolongation.",
        )
    mode = await mode_egalite_eliminatoire(db, match)
    if mode == MODE_PROLONGATIONS_2X15:
        if current == "2" and est_a_egalite(match):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Égalité après 90 minutes : démarrez les prolongations (2 × 15 minutes) avant de terminer le match.",
            )
        if current == "3" or current == "mi_temps_et":
            raise HTTPException(status.HTTP_409_CONFLICT, "Les deux périodes de prolongation doivent être terminées.")


async def verifier_tirs_autorises(db: AsyncSession, match: Match) -> None:
    """Ne laisse pas commencer la séance avant la fin prévue par le règlement."""
    if _value(match.phase) not in PHASES_ELIMINATOIRES or not est_a_egalite(match):
        return
    mode = await mode_egalite_eliminatoire(db, match)
    current = _value(match.periode)
    if mode == MODE_PROLONGATIONS_2X15 and current != "4":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Le règlement prévoit deux périodes de prolongation avant les tirs au but.",
        )


async def verifier_resultat_eliminatoire_validable(db: AsyncSession, match: Match) -> None:
    """Garde aussi le chemin service/synchronisation, pas seulement la route HTTP."""
    if _value(match.phase) not in PHASES_ELIMINATOIRES or match.forfait:
        return
    mode = await mode_egalite_eliminatoire(db, match)
    current = _value(match.periode)
    if mode == MODE_PROLONGATIONS_2X15:
        if current in PERIODES_PROLONGATION and current != "4":
            raise HTTPException(status.HTTP_409_CONFLICT, "Les prolongations ne sont pas terminées.")
        if est_a_egalite(match) and current != "4":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Égalité : le match doit atteindre la fin des prolongations avant les tirs au but.",
            )
    if est_a_egalite(match):
        from app.services.tirs_au_but import vainqueur_tirs_au_but

        if vainqueur_tirs_au_but(match.tirs_au_but or []) is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Match éliminatoire à égalité : terminez la séance de tirs au but avant validation.",
            )


def duree_officielle_match_minutes(match: Match) -> int:
    """Durée conventionnelle pour les participations complètes à cette rencontre."""
    period = _value(match.periode)
    if period == "4":
        return 120
    if period in ("3", "mi_temps_et"):
        return 105
    if period in ("2", "mi_temps"):
        return 90
    if period == "1":
        return 45
    return 90
