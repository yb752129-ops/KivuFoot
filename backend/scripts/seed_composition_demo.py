"""Crée un environnement DEMO isolé pour tester la composition professionnelle.

Ce script est volontairement séparé de la compétition réelle et de
``seed_demo.py``. Il ne doit être exécuté que sur une base de démonstration
ou de préproduction, jamais sur la base du championnat en cours.

Usage :
    DATABASE_URL=postgresql+asyncpg://... python -m scripts.seed_composition_demo

Le script est idempotent par nom de compétition : une seconde exécution ne
crée pas une nouvelle édition.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.auth.hashing import hash_password
from app.database import AsyncSessionLocal
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.enums import (
    PosteJoueur,
    RoleStaff,
    RoleUtilisateur,
    StatutJoueur,
    StatutMatch,
    TypeCompetition,
)
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.staff import Staff
from app.models.user import User


DEMO_COMPETITION_NOM = "DEMO - Composition professionnelle"
DEMO_PASSWORD = "ChangeMoiEnDemo123!"
COACH_EMAIL = "coach.composition.demo@example.com"
MANAGER_EMAIL = "manager.composition.demo@example.com"
ORGA_EMAIL = "orga.composition.demo@example.com"


async def _get_or_create_user(db, email: str, role: RoleUtilisateur, name: str, club_id: int | None = None):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            mot_de_passe_hash=hash_password(DEMO_PASSWORD),
            role=role,
            nom_complet=name,
            club_id=club_id,
            est_actif=True,
        )
        db.add(user)
    else:
        user.mot_de_passe_hash = hash_password(DEMO_PASSWORD)
        user.role = role
        user.nom_complet = name
        user.club_id = club_id
        user.est_actif = True
    await db.flush()
    return user


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(Competition).where(Competition.nom == DEMO_COMPETITION_NOM))
        ).scalar_one_or_none()
        if existing is not None:
            saison = (
                await db.execute(select(Saison).where(Saison.competition_id == existing.id).order_by(Saison.id))
            ).scalars().first()
            match_ = (
                await db.execute(select(Match).where(Match.saison_id == saison.id).order_by(Match.id))
            ).scalars().first() if saison else None
            print("La démonstration existe déjà — aucune donnée réelle n'a été touchée.")
            print(f"competition_id={existing.id} saison_id={getattr(saison, 'id', None)} match_id={getattr(match_, 'id', None)}")
            print(f"coach={COACH_EMAIL} manager={MANAGER_EMAIL} mot_de_passe={DEMO_PASSWORD}")
            return

        competition = Competition(
            nom=DEMO_COMPETITION_NOM,
            type=TypeCompetition.CHAMPIONNAT,
            saison_label="DEMO-COMPOSITION",
            est_demo=True,
        )
        db.add(competition)
        await db.flush()

        saison = Saison(
            competition_id=competition.id,
            nom="Saison démo composition",
            date_debut=date.today(),
            date_fin=date.today() + timedelta(days=180),
        )
        db.add(saison)
        await db.flush()

        club_a = Club(nom="DEMO Composition A", ville="Bukavu", stade="Terrain DEMO A")
        club_b = Club(nom="DEMO Composition B", ville="Bukavu", stade="Terrain DEMO B")
        db.add_all([club_a, club_b])
        await db.flush()
        db.add_all([
            SaisonClub(saison_id=saison.id, club_id=club_a.id),
            SaisonClub(saison_id=saison.id, club_id=club_b.id),
        ])

        orga = await _get_or_create_user(db, ORGA_EMAIL, RoleUtilisateur.ORGANISATEUR, "Organisateur composition DEMO")
        await _get_or_create_user(db, COACH_EMAIL, RoleUtilisateur.COACH, "Coach composition DEMO", club_a.id)
        await _get_or_create_user(db, MANAGER_EMAIL, RoleUtilisateur.CLUB_MANAGER, "Manager composition DEMO", club_a.id)
        db.add(OrganisateurCompetition(user_id=orga.id, competition_id=competition.id))

        postes = (
            [PosteJoueur.GARDIEN] * 2
            + [PosteJoueur.DEFENSEUR] * 6
            + [PosteJoueur.MILIEU] * 6
            + [PosteJoueur.ATTAQUANT] * 5
        )
        for club, prefix in ((club_a, "A"), (club_b, "B")):
            joueurs = []
            for index, poste in enumerate(postes, start=1):
                joueur = Joueur(
                    nom_complet=f"DEMO {prefix} Joueur {index}",
                    date_naissance=date(1995 + (index % 8), (index % 12) + 1, (index % 25) + 1),
                    poste=poste,
                    statut=StatutJoueur.ACTIF,
                    club_actuel_id=club.id,
                    numero=index,
                )
                joueurs.append(joueur)
            # Cas de test de nom long, explicitement DEMO.
            joueurs[-1].nom_complet = f"DEMO {prefix} Joueur avec un nom volontairement très long pour vérifier l'affichage mobile"
            # Cas de test d'éligibilité : visible dans l'effectif mais bloqué.
            joueurs[-2].statut = StatutJoueur.SUSPENDU
            db.add_all(joueurs)

            db.add(
                Staff(
                    club_id=club.id,
                    nom_complet=f"Entraîneur principal DEMO {prefix}",
                    role=RoleStaff.ENTRAINEUR_PRINCIPAL,
                    statut=StatutJoueur.ACTIF,
                )
            )
        await db.flush()

        now = datetime.now(timezone.utc)
        match_ = Match(
            saison_id=saison.id,
            journee="J1-DEMO",
            date_heure=now + timedelta(days=3),
            stade="Terrain DEMO A",
            equipe_domicile_id=club_a.id,
            equipe_exterieur_id=club_b.id,
            statut=StatutMatch.PROGRAMME,
        )
        db.add(match_)
        await db.flush()
        await db.commit()

        print("Démonstration de composition créée sur une base isolée.")
        print(f"competition_id={competition.id} saison_id={saison.id} match_id={match_.id}")
        print(f"URL coach : /coach/matchs/{match_.id}/composition")
        print(f"URL club  : /club/matchs/{match_.id}/composition")
        print(f"coach={COACH_EMAIL} manager={MANAGER_EMAIL} mot_de_passe={DEMO_PASSWORD}")
        print("Données créées : 2 clubs DEMO, 19 joueurs par club, 1 joueur suspendu par club, 1 staff par club.")


if __name__ == "__main__":
    asyncio.run(seed())
