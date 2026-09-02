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
from app.models.enums import EquipeConcernee, ResultatPenalty, StatutParticipation, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match, MatchParticipation
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

    elif evenement.type == TypeEvenement.REMPLACEMENT:
        minute_eff = evenement.minute + (evenement.minute_additionnelle or 0)
        if evenement.joueur_id:
            result = await db.execute(
                select(MatchParticipation).where(
                    MatchParticipation.match_id == match_.id,
                    MatchParticipation.joueur_id == evenement.joueur_id,
                )
            )
            sortant = result.scalar_one_or_none()
            if sortant is not None and sortant.minute_sortie is None:
                sortant.minute_sortie = minute_eff
        if evenement.joueur_secondaire_id:
            result = await db.execute(
                select(MatchParticipation).where(
                    MatchParticipation.match_id == match_.id,
                    MatchParticipation.joueur_id == evenement.joueur_secondaire_id,
                )
            )
            entrant = result.scalar_one_or_none()
            club_id = (
                match_.equipe_exterieur_id
                if evenement.equipe_concernee == EquipeConcernee.EXTERIEUR
                else match_.equipe_domicile_id
            )
            if entrant is not None:
                if entrant.minute_entree == 0:
                    entrant.minute_entree = minute_eff
            elif club_id:
                db.add(
                    MatchParticipation(
                        match_id=match_.id,
                        joueur_id=evenement.joueur_secondaire_id,
                        club_id=club_id,
                        equipe_concernee=evenement.equipe_concernee,
                        statut=StatutParticipation.REMPLACANT.value,
                        minute_entree=minute_eff,
                    )
                )

    if but_marque_pour == EquipeConcernee.DOMICILE:
        match_.score_domicile += 1
    elif but_marque_pour == EquipeConcernee.EXTERIEUR:
        match_.score_exterieur += 1


def _dec(stat: StatistiqueJoueur, champ: str) -> None:
    val = getattr(stat, champ) or 0
    setattr(stat, champ, max(0, val - 1))


async def retirer_evenement_valide(db: AsyncSession, evenement: EvenementMatch, match_: Match) -> None:
    """Inverse de appliquer_evenement_valide — refus arbitral, jamais un DELETE."""
    saison = await db.get(Saison, match_.saison_id)
    competition_id = saison.competition_id if saison else None
    but_pour = None

    if evenement.type == TypeEvenement.BUT:
        but_pour = evenement.equipe_concernee
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            _dec(stat, "buts")

    elif evenement.type == TypeEvenement.PENALTY and evenement.resultat == ResultatPenalty.MARQUE:
        but_pour = evenement.equipe_concernee
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            _dec(stat, "buts")

    elif evenement.type == TypeEvenement.BUT_CONTRE_SON_CAMP:
        but_pour = _equipe_opposee(evenement.equipe_concernee)

    elif evenement.type == TypeEvenement.PASSE_DECISIVE:
        if evenement.joueur_secondaire_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_secondaire_id, competition_id, match_.saison_id)
            _dec(stat, "passes_decisives")

    elif evenement.type == TypeEvenement.CARTON_JAUNE:
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            _dec(stat, "cartons_jaunes")

    elif evenement.type == TypeEvenement.CARTON_ROUGE:
        if evenement.joueur_id and competition_id:
            stat = await _get_or_create_stat(db, evenement.joueur_id, competition_id, match_.saison_id)
            _dec(stat, "cartons_rouges")

    if but_pour == EquipeConcernee.DOMICILE:
        match_.score_domicile = max(0, match_.score_domicile - 1)
    elif but_pour == EquipeConcernee.EXTERIEUR:
        match_.score_exterieur = max(0, match_.score_exterieur - 1)
