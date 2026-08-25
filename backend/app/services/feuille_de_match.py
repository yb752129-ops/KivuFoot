"""
Calcule matchs_joues / titularisations / minutes_jouees à partir de
match_participations (feuille de match) - jamais à partir de
joueurs.club_actuel_id (décision C2, voir modèle MatchParticipation).

Appelé à la validation finale du match (pas événement par événement),
car les minutes définitives ne sont connues qu'une fois tous les
remplacements traités.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Saison
from app.models.enums import StatutParticipation
from app.models.match import Match, MatchParticipation
from app.models.stats import StatistiqueJoueur


async def _get_or_create_stat(
    db: AsyncSession, joueur_id: int, competition_id: int, saison_id: int
) -> StatistiqueJoueur:
    result = await db.execute(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur_id,
            StatistiqueJoueur.competition_id == competition_id,
            StatistiqueJoueur.saison_id == saison_id,
        )
    )
    stat = result.scalar_one_or_none()
    if stat is None:
        stat = StatistiqueJoueur(joueur_id=joueur_id, competition_id=competition_id, saison_id=saison_id)
        db.add(stat)
        await db.flush()
    return stat


DUREE_MATCH_MINUTES = 90


async def appliquer_feuille_de_match(db: AsyncSession, match_: Match) -> None:
    saison = await db.get(Saison, match_.saison_id)
    if saison is None:
        return
    competition_id = saison.competition_id

    result = await db.execute(select(MatchParticipation).where(MatchParticipation.match_id == match_.id))
    participations = result.scalars().all()

    for p in participations:
        stat = await _get_or_create_stat(db, p.joueur_id, competition_id, match_.saison_id)
        stat.matchs_joues += 1
        if p.statut == StatutParticipation.TITULAIRE:
            stat.titularisations += 1
        minute_fin = p.minute_sortie if p.minute_sortie is not None else DUREE_MATCH_MINUTES
        minutes = max(0, minute_fin - p.minute_entree)
        stat.minutes_jouees += minutes
