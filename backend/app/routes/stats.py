from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.actualite import HommeMatch
from app.models.club import Club
from app.models.enums import ResultatPenalty, RoleUtilisateur, StatutMatch, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.stats import StatistiqueJoueur
from app.models.user import User
from app.schemas.sync import TopStatLigne

router = APIRouter(prefix="/stats", tags=["Statistiques"])


@router.get("/joueur/{joueur_id}/public")
async def stats_joueur_public(
    joueur_id: int,
    saison_id: int,
    db: AsyncSession = Depends(get_db),
):
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None or joueur.anonymise or joueur.fusionne:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    stat = await db.scalar(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur_id,
            StatistiqueJoueur.saison_id == saison_id,
        )
    )
    buts_penaltys = await db.execute(
        select(EvenementMatch.resultat, EvenementMatch.id)
        .join(Match, Match.id == EvenementMatch.match_id)
        .where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
            EvenementMatch.joueur_id == joueur_id,
            EvenementMatch.type == TypeEvenement.PENALTY,
            EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
            EvenementMatch.refuse.is_(False),
        )
    )
    penalty_rows = buts_penaltys.all()
    homme_du_match = await db.scalar(
        select(func.count(HommeMatch.id))
        .join(Match, Match.id == HommeMatch.match_id)
        .where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
            HommeMatch.joueur_id == joueur_id,
        )
    )
    values = stat or StatistiqueJoueur(
        joueur_id=joueur_id,
        competition_id=0,
        saison_id=saison_id,
    )
    return {
        "joueur_id": joueur.id,
        "joueur_nom": joueur.nom_complet,
        "club_actuel_id": joueur.club_actuel_id,
        "saison_id": saison_id,
        "matchs_joues": values.matchs_joues,
        "titularisations": values.titularisations,
        "minutes_jouees": values.minutes_jouees,
        "buts": values.buts,
        "passes_decisives": values.passes_decisives,
        "cartons_jaunes": values.cartons_jaunes,
        "cartons_rouges": values.cartons_rouges,
        "penalties_marques": sum(1 for resultat, _ in penalty_rows if resultat == ResultatPenalty.MARQUE),
        "penalties_rates": sum(1 for resultat, _ in penalty_rows if resultat == ResultatPenalty.RATE),
        "hommes_du_match": int(homme_du_match or 0),
        "source": "matchs_officiellement_valides",
    }


@router.get("/joueur/{joueur_id}")
async def stats_joueur(
    joueur_id: int,
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.CLUB_MANAGER)
    ),
):
    """Réservé (§11.8) : stats détaillées, potentiellement sensibles pour un mineur (§7.4)."""
    result = await db.execute(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur_id, StatistiqueJoueur.saison_id == saison_id
        )
    )
    stats = result.scalars().all()
    if not stats:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune statistique pour ce joueur sur cette saison.")
    return stats


async def _top(db: AsyncSession, saison_id: int, colonne, limit: int) -> list[TopStatLigne]:
    result = await db.execute(
        select(StatistiqueJoueur, Joueur, Club)
        .join(Joueur, Joueur.id == StatistiqueJoueur.joueur_id)
        .outerjoin(Club, Club.id == Joueur.club_actuel_id)
        .options(selectinload(Joueur.photo_actuelle_rel))
        .where(StatistiqueJoueur.saison_id == saison_id, Joueur.anonymise.is_(False))
        .order_by(colonne.desc(), Joueur.nom_complet.asc())
        .limit(min(limit, 50))
    )
    lignes = []
    for stat, joueur, club in result.all():
        lignes.append(
            TopStatLigne(
                joueur_id=joueur.id,
                joueur_nom=joueur.nom_complet,
                club_id=club.id if club else None,
                club_nom=club.nom if club else None,
                photo_url=joueur.photo_url,
                valeur=getattr(stat, colonne.key),
            )
        )
    return lignes


@router.get("/meilleurs-buteurs", response_model=list[TopStatLigne])
async def meilleurs_buteurs(saison_id: int, db: AsyncSession = Depends(get_db), limit: int = 10):
    return await _top(db, saison_id, StatistiqueJoueur.buts, limit)


@router.get("/meilleurs-passeurs", response_model=list[TopStatLigne])
async def meilleurs_passeurs(saison_id: int, db: AsyncSession = Depends(get_db), limit: int = 10):
    return await _top(db, saison_id, StatistiqueJoueur.passes_decisives, limit)
