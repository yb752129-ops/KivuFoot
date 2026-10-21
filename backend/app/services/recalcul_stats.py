"""Reconstruction des agrégats joueurs à partir des faits officiels.

Les lignes de ``statistiques_joueurs`` sont une vue matérialisée historique.
Un changement de statut d'un match ne peut donc pas seulement décrémenter un
compteur : cette reconstruction supprime puis recrée les agrégats de la
saison depuis les participations et événements conservés, uniquement pour les
matchs officiellement valides.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Saison
from app.models.enums import (
    ResultatPenalty,
    StatutMatch,
    StatutParticipation,
    StatutValidationEvenement,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.match import Match, MatchParticipation
from app.models.stats import StatistiqueJoueur


DUREE_MATCH_MINUTES = 90


def _value(value):
    return value.value if hasattr(value, "value") else value


async def reconstruire_stats_saison(db: AsyncSession, saison_id: int) -> None:
    """Reconstruit tous les agrégats d'une saison, sans toucher aux faits.

    Les événements d'un match annulé restent en base mais ne sont jamais
    sélectionnés ici. La fonction est volontairement idempotente : elle peut
    être appelée aussi bien à l'annulation qu'au rétablissement.
    """
    saison = await db.get(Saison, saison_id)
    if saison is None:
        return

    existants = (
        await db.execute(
            select(StatistiqueJoueur).where(StatistiqueJoueur.saison_id == saison_id)
        )
    ).scalars().all()
    for stat in existants:
        await db.delete(stat)
    await db.flush()

    stats_by_player: dict[int, StatistiqueJoueur] = {}

    def get_stat(joueur_id: int) -> StatistiqueJoueur:
        stat = stats_by_player.get(joueur_id)
        if stat is None:
            stat = StatistiqueJoueur(
                joueur_id=joueur_id,
                competition_id=saison.competition_id,
                saison_id=saison_id,
                matchs_joues=0,
                titularisations=0,
                buts=0,
                passes_decisives=0,
                cartons_jaunes=0,
                cartons_rouges=0,
                minutes_jouees=0,
            )
            stats_by_player[joueur_id] = stat
            db.add(stat)
        return stat

    matchs_valides = (
        await db.execute(
            select(Match).where(
                Match.saison_id == saison_id,
                Match.statut == StatutMatch.VALIDE,
            )
        )
    ).scalars().all()
    match_ids = [match.id for match in matchs_valides]

    if match_ids:
        participations = (
            await db.execute(
                select(MatchParticipation).where(MatchParticipation.match_id.in_(match_ids))
            )
        ).scalars().all()
        for participation in participations:
            stat = get_stat(participation.joueur_id)
            stat.matchs_joues += 1
            if _value(participation.statut) == StatutParticipation.TITULAIRE.value:
                stat.titularisations += 1
            minute_fin = (
                participation.minute_sortie
                if participation.minute_sortie is not None
                else DUREE_MATCH_MINUTES
            )
            stat.minutes_jouees += max(0, minute_fin - participation.minute_entree)

        evenements = (
            await db.execute(
                select(EvenementMatch).where(
                    EvenementMatch.match_id.in_(match_ids),
                    EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                    EvenementMatch.refuse.is_(False),
                )
            )
        ).scalars().all()
        for evenement in evenements:
            type_evenement = _value(evenement.type)
            if type_evenement == TypeEvenement.BUT.value:
                if evenement.joueur_id:
                    get_stat(evenement.joueur_id).buts += 1
            elif (
                type_evenement == TypeEvenement.PENALTY.value
                and _value(evenement.resultat) == ResultatPenalty.MARQUE.value
            ):
                if evenement.joueur_id:
                    get_stat(evenement.joueur_id).buts += 1
            elif type_evenement == TypeEvenement.PASSE_DECISIVE.value:
                if evenement.joueur_secondaire_id:
                    get_stat(evenement.joueur_secondaire_id).passes_decisives += 1
            elif type_evenement == TypeEvenement.CARTON_JAUNE.value:
                if evenement.joueur_id:
                    get_stat(evenement.joueur_id).cartons_jaunes += 1
            elif type_evenement == TypeEvenement.CARTON_ROUGE.value:
                if evenement.joueur_id:
                    get_stat(evenement.joueur_id).cartons_rouges += 1

    await db.flush()
