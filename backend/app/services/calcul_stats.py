"""
Application des effets d'un événement VALIDÉ sur :
- le score du match
- les statistiques individuelles du joueur (statistiques_joueurs)

RÈGLES CRITIQUES (voir rapport Phase 0, point A1) :
- Un penalty marqué (type='penalty', resultat='marque') compte comme un
  but à part entière. Il ne doit JAMAIS exister d'événement 'but'
  supplémentaire pour le même fait de jeu - c'est une règle de saisie
  appliquée en amont (schémas + formation des collecteurs), le calcul
  ici fait simplement confiance à statut_validation='valide' et ne
  peut pas détecter une double-saisie a posteriori autrement qu'en
  comparant les minutes/joueurs (voir services/detection_doublons.py
  pour les événements, à activer si besoin en V2).
- Un but contre son camp (but_contre_son_camp) crédite le score de
  l'ÉQUIPE ADVERSE à celle du joueur, mais NE crédite PAS le compteur
  `buts` du joueur (ce n'est pas une performance individuelle positive).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Saison
from app.models.enums import EquipeConcernee, ResultatPenalty, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.stats import StatistiqueJoueur


def _equipe_opposee(equipe: EquipeConcernee) -> EquipeConcernee:
    return EquipeConcernee.EXTERIEUR if equipe == EquipeConcernee.DOMICILE else EquipeConcernee.DOMICILE


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


async def appliquer_evenement_valide(db: AsyncSession, evenement: EvenementMatch, match_: Match) -> None:
    """Met à jour le score du match et les stats joueurs pour un événement qui vient d'être validé."""
    saison = await db.get(Saison, match_.saison_id)
    competition_id = saison.competition_id if saison else None

    but_marque_pour = None  # équipe créditée du but au score

    if evenement.type == TypeEvenement.BUT:
        but_marque_pour = evenement.equipe_concernee
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            stat.buts += 1

    elif evenement.type == TypeEvenement.PENALTY and evenement.resultat == ResultatPenalty.MARQUE:
        but_marque_pour = evenement.equipe_concernee
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            stat.buts += 1
        # penalty raté : aucun effet sur le score ni les stats de buts.

    elif evenement.type == TypeEvenement.BUT_CONTRE_SON_CAMP:
        # Le but est crédité à l'équipe ADVERSE de celle du joueur fautif.
        but_marque_pour = _equipe_opposee(evenement.equipe_concernee)
        # Volontairement : pas de crédit dans les stats individuelles du joueur.

    elif evenement.type == TypeEvenement.PASSE_DECISIVE:
        if evenement.joueur_secondaire_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_secondaire_id, competition_id, match_.saison_id)
            stat.passes_decisives += 1

    elif evenement.type == TypeEvenement.CARTON_JAUNE:
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            stat.cartons_jaunes += 1

    elif evenement.type == TypeEvenement.CARTON_ROUGE:
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            stat.cartons_rouges += 1

    # REMPLACEMENT : n'affecte pas le score ; les minutes jouées sont
    # dérivées de match_participations (voir services/feuille_de_match.py).

    if but_marque_pour == EquipeConcernee.DOMICILE:
        match_.score_domicile += 1
    elif but_marque_pour == EquipeConcernee.EXTERIEUR:
        match_.score_exterieur += 1
