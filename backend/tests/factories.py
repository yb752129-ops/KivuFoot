from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.hashing import hash_password
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison
from app.models.enums import PosteJoueur, RoleUtilisateur, TypeCompetition
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.user import User


async def creer_utilisateur(db: AsyncSession, role: RoleUtilisateur, email: str, club_id: int | None = None) -> User:
    user = User(
        email=email,
        mot_de_passe_hash=hash_password("TestPassword123!"),
        role=role,
        nom_complet=f"Test {role}",
        club_id=club_id,
    )
    db.add(user)
    await db.flush()
    return user


async def creer_club(db: AsyncSession, nom: str = "TEST FC") -> Club:
    club = Club(nom=nom, ville="Bukavu")
    db.add(club)
    await db.flush()
    return club


async def creer_competition_avec_saison(db: AsyncSession, organisateur: User | None = None, est_demo: bool = True):
    competition = Competition(
        nom="DEMO - Compétition de test", type=TypeCompetition.CHAMPIONNAT, est_demo=est_demo
    )
    db.add(competition)
    await db.flush()
    if organisateur is not None:
        db.add(OrganisateurCompetition(user_id=organisateur.id, competition_id=competition.id))
    saison = Saison(competition_id=competition.id, nom="Saison test")
    db.add(saison)
    await db.flush()
    return competition, saison


async def creer_joueur(db: AsyncSession, club_id: int, nom: str = "Joueur Test") -> Joueur:
    joueur = Joueur(nom_complet=nom, date_naissance=date(2000, 1, 1), poste=PosteJoueur.ATTAQUANT, club_actuel_id=club_id)
    db.add(joueur)
    await db.flush()
    return joueur


async def creer_match(db: AsyncSession, saison_id: int, club_dom_id: int, club_ext_id: int) -> Match:
    match_ = Match(
        saison_id=saison_id,
        date_heure=datetime.now(timezone.utc) + timedelta(days=1),
        equipe_domicile_id=club_dom_id,
        equipe_exterieur_id=club_ext_id,
    )
    db.add(match_)
    await db.flush()
    return match_
