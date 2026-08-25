"""
Génère des données de DÉMONSTRATION, clairement identifiées et jamais
mélangées aux données réelles (règle non négociable de la spécification).

- La compétition démo est nommée "DEMO - Championnat de test" et porte
  `est_demo=True`.
- Aucun nom de club, joueur ou compétition réel n'est utilisé.
- Ce script est idempotent : le relancer ne duplique pas les données
  (il vérifie l'existence de la compétition démo avant de créer quoi
  que ce soit).

Usage :
    python -m scripts.seed_demo
"""
import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.auth.hashing import hash_password
from app.database import AsyncSessionLocal
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.enums import PosteJoueur, RoleUtilisateur, TypeCompetition
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.user import User

DEMO_COMPETITION_NOM = "DEMO - Championnat de test"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Competition).where(Competition.nom == DEMO_COMPETITION_NOM))
        if existing.scalar_one_or_none() is not None:
            print("Les données DEMO existent déjà - rien à faire (script idempotent).")
            return

        # --- Utilisateurs de démonstration ---
        admin = User(
            email="admin@demo.kivufoot.local",
            mot_de_passe_hash=hash_password("ChangeMoiEnDemo123!"),
            role=RoleUtilisateur.ADMIN,
            nom_complet="Admin Démo",
        )
        organisateur = User(
            email="organisateur@demo.kivufoot.local",
            mot_de_passe_hash=hash_password("ChangeMoiEnDemo123!"),
            role=RoleUtilisateur.ORGANISATEUR,
            nom_complet="Organisateur Démo",
        )
        collecteur = User(
            email="collecteur@demo.kivufoot.local",
            mot_de_passe_hash=hash_password("ChangeMoiEnDemo123!"),
            role=RoleUtilisateur.COLLECTEUR,
            nom_complet="Collecteur Démo",
        )
        db.add_all([admin, organisateur, collecteur])
        await db.flush()

        # --- Compétition / saison DEMO ---
        competition = Competition(
            nom=DEMO_COMPETITION_NOM, type=TypeCompetition.CHAMPIONNAT, saison_label="2026-DEMO", est_demo=True
        )
        db.add(competition)
        await db.flush()

        db.add(OrganisateurCompetition(user_id=organisateur.id, competition_id=competition.id))

        saison = Saison(
            competition_id=competition.id,
            nom="Saison démo 2026",
            date_debut=date.today(),
            date_fin=date.today() + timedelta(days=180),
        )
        db.add(saison)
        await db.flush()

        # --- Clubs DEMO (noms fictifs, jamais de club réel) ---
        club_a = Club(nom="DEMO FC Alpha", ville="Bukavu", stade="Terrain d'essai A")
        club_b = Club(nom="DEMO FC Beta", ville="Bukavu", stade="Terrain d'essai B")
        db.add_all([club_a, club_b])
        await db.flush()

        db.add_all([
            SaisonClub(saison_id=saison.id, club_id=club_a.id),
            SaisonClub(saison_id=saison.id, club_id=club_b.id),
        ])

        club_manager = User(
            email="club-manager@demo.kivufoot.local",
            mot_de_passe_hash=hash_password("ChangeMoiEnDemo123!"),
            role=RoleUtilisateur.CLUB_MANAGER,
            nom_complet="Manager Démo",
            club_id=club_a.id,
        )
        db.add(club_manager)

        # --- Joueurs DEMO ---
        joueurs_a = [
            Joueur(nom_complet=f"Joueur Démo A{i}", date_naissance=date(1999, 1, i + 1), poste=PosteJoueur.ATTAQUANT, club_actuel_id=club_a.id)
            for i in range(1, 4)
        ]
        joueurs_b = [
            Joueur(nom_complet=f"Joueur Démo B{i}", date_naissance=date(1998, 2, i + 1), poste=PosteJoueur.DEFENSEUR, club_actuel_id=club_b.id)
            for i in range(1, 4)
        ]
        db.add_all(joueurs_a + joueurs_b)
        await db.flush()

        # --- Match DEMO programmé (statut initial, aucune donnée validée) ---
        match_demo = Match(
            saison_id=saison.id,
            journee="J1",
            date_heure=datetime.now(timezone.utc) + timedelta(days=1),
            stade=club_a.stade,
            equipe_domicile_id=club_a.id,
            equipe_exterieur_id=club_b.id,
        )
        db.add(match_demo)

        await db.commit()
        print(f"Données DEMO créées : compétition '{DEMO_COMPETITION_NOM}' (id={competition.id}).")
        print("Comptes de démonstration (mot de passe : ChangeMoiEnDemo123!) :")
        print("  admin@demo.kivufoot.local / organisateur@demo.kivufoot.local")
        print("  club-manager@demo.kivufoot.local / collecteur@demo.kivufoot.local")


if __name__ == "__main__":
    asyncio.run(seed())
