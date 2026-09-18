"""Règles communes pour les groupes officiels d'une saison.

La colonne ``saison_clubs.groupe`` est la source de vérité. ``matchs.groupe``
reste une copie d'affichage/compatibilité et ne doit jamais permettre de
programmer une poule contradictoire.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import SaisonClub

GROUPES_VALIDES = frozenset({"A", "B", "C", "D"})


def _valeur_groupe(groupe) -> str | None:
    if groupe is None:
        return None
    return getattr(groupe, "value", groupe)


async def groupes_officiels_pour_clubs(
    db: AsyncSession,
    saison_id: int,
    club_ids: set[int] | list[int] | tuple[int, ...],
) -> dict[int, str | None]:
    """Retourne le groupe officiel de chaque inscription demandée."""
    ids = set(club_ids)
    if not ids:
        return {}
    result = await db.execute(
        select(SaisonClub.club_id, SaisonClub.groupe).where(
            SaisonClub.saison_id == saison_id,
            SaisonClub.club_id.in_(ids),
        )
    )
    return {club_id: _valeur_groupe(groupe) for club_id, groupe in result.all()}


async def determiner_groupe_match(
    db: AsyncSession,
    saison_id: int,
    equipe_domicile_id: int,
    equipe_exterieur_id: int,
    phase: str,
    groupe_demande=None,
) -> str | None:
    """Valide et, pour une poule, déduit le groupe officiel du match.

    Une poule ne peut être créée que si les deux inscriptions existent et
    portent le même groupe A/B/C/D. Le groupe saisi par le client est accepté
    seulement s'il correspond à cette source officielle.
    """
    phase_value = getattr(phase, "value", phase)
    demande = _valeur_groupe(groupe_demande)
    if demande is not None and demande not in GROUPES_VALIDES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Groupe inconnu : A, B, C ou D.")

    groupes = await groupes_officiels_pour_clubs(
        db,
        saison_id,
        {equipe_domicile_id, equipe_exterieur_id},
    )
    if equipe_domicile_id not in groupes or equipe_exterieur_id not in groupes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Les deux équipes doivent être inscrites à cette saison.",
        )

    if phase_value != "poule":
        return demande

    groupe_domicile = groupes[equipe_domicile_id]
    groupe_exterieur = groupes[equipe_exterieur_id]
    if not groupe_domicile or not groupe_exterieur:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Affectez d'abord un groupe officiel aux deux équipes.",
        )
    if groupe_domicile != groupe_exterieur:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Un match de poule doit opposer deux équipes du même groupe officiel.",
        )
    if demande is not None and demande != groupe_domicile:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Le groupe du match doit être {groupe_domicile} pour ces deux équipes.",
        )
    return groupe_domicile
