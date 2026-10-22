"""Règles partagées pour le statut d'une équipe dans une édition.

Le statut est porté par la ligne ``saison_clubs`` : un même club peut donc
être actif dans une édition et retiré dans une autre. Cette projection ne
supprime jamais de donnée et ne touche pas aux matchs.
"""

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import SaisonClub
from app.models.enums import StatutEquipeEdition
from app.models.match import Match


def match_sans_equipe_retiree(match_model=Match):
    """Expression SQL : le match reste représentable dans le public.

    Elle est volontairement corrélée à ``Match.saison_id``. Les équipes
    disqualifiées/éliminées ne sont pas concernées : seuls les retraits
    sortent de la projection publique.
    """

    return ~exists(
        select(SaisonClub.club_id).where(
            SaisonClub.saison_id == match_model.saison_id,
            SaisonClub.statut == StatutEquipeEdition.RETIRE.value,
            or_(
                SaisonClub.club_id == match_model.equipe_domicile_id,
                SaisonClub.club_id == match_model.equipe_exterieur_id,
            ),
        )
    )


async def match_a_une_equipe_retiree(db: AsyncSession, match: Match) -> bool:
    """Vérifie une visibilité publique de détail sans réécrire le match."""

    result = await db.execute(
        select(SaisonClub.club_id).where(
            SaisonClub.saison_id == match.saison_id,
            SaisonClub.statut == StatutEquipeEdition.RETIRE.value,
            or_(
                SaisonClub.club_id == match.equipe_domicile_id,
                SaisonClub.club_id == match.equipe_exterieur_id,
            ),
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def equipe_retiree_dans_saison(db: AsyncSession, saison_id: int, club_id: int) -> bool:
    return await db.scalar(
        select(exists().where(
            SaisonClub.saison_id == saison_id,
            SaisonClub.club_id == club_id,
            SaisonClub.statut == StatutEquipeEdition.RETIRE.value,
        ))
    ) or False


async def statut_equipe_dans_saison(
    db: AsyncSession,
    saison_id: int,
    club_id: int,
) -> StatutEquipeEdition | None:
    return await db.scalar(
        select(SaisonClub.statut).where(
            SaisonClub.saison_id == saison_id,
            SaisonClub.club_id == club_id,
        )
    )
