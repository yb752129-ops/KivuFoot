"""
Données de DÉMONSTRATION, clairement identifiées (est_demo=True).
Idempotent : relancer ne duplique rien.

Usage :
    python -m scripts.seed_demo
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.auth.hashing import hash_password
from app.database import AsyncSessionLocal
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.enums import (
    EquipeConcernee,
    PosteJoueur,
    RoleUtilisateur,
    StatutMatch,
    StatutValidationEvenement,
    TypeCompetition,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.user import User

DEMO_COMPETITION_NOM = "DEMO - Championnat de test"
DEMO_PASSWORD = "ChangeMoiEnDemo123!"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Competition).where(Competition.nom == DEMO_COMPETITION_NOM))
        if existing.scalar_one_or_none() is not None:
            print("Les données DEMO existent déjà - rien à faire (script idempotent).")
            return

        admin = User(
            email="admin.demo@example.com",
            mot_de_passe_hash=hash_password(DEMO_PASSWORD),
            role=RoleUtilisateur.ADMIN,
            nom_complet="Admin Démo",
        )
        organisateur = User(
            email="orga.demo@example.com",
            mot_de_passe_hash=hash_password(DEMO_PASSWORD),
            role=RoleUtilisateur.ORGANISATEUR,
            nom_complet="Organisateur Démo",
        )
        collecteur = User(
            email="collecteur.demo@example.com",
            mot_de_passe_hash=hash_password(DEMO_PASSWORD),
            role=RoleUtilisateur.COLLECTEUR,
            nom_complet="Collecteur Démo",
        )
        db.add_all([admin, organisateur, collecteur])
        await db.flush()

        competition = Competition(
            nom=DEMO_COMPETITION_NOM,
            type=TypeCompetition.CHAMPIONNAT,
            saison_label="2026-DEMO",
            est_demo=True,
        )
        db.add(competition)
        await db.flush()
        db.add(OrganisateurCompetition(user_id=organisateur.id, competition_id=competition.id))

        saison = Saison(
            competition_id=competition.id,
            nom="Saison démo 2026",
            date_debut=date.today() - timedelta(days=30),
            date_fin=date.today() + timedelta(days=150),
        )
        db.add(saison)
        await db.flush()

        clubs_data = [
            ("DEMO FC Kadutu", "Bukavu", "Stade Kadutu"),
            ("DEMO FC Ibanda", "Bukavu", "Stade Ibanda"),
            ("DEMO AS Bagira", "Bukavu", "Terrain Bagira"),
            ("DEMO AS Uvira", "Uvira", "Stade Uvira"),
        ]
        clubs = [Club(nom=n, ville=v, stade=s) for n, v, s in clubs_data]
        db.add_all(clubs)
        await db.flush()
        kadutu, ibanda, bagira, uvira = clubs

        db.add_all([SaisonClub(saison_id=saison.id, club_id=c.id) for c in clubs])

        club_manager = User(
            email="manager.demo@example.com",
            mot_de_passe_hash=hash_password(DEMO_PASSWORD),
            role=RoleUtilisateur.CLUB_MANAGER,
            nom_complet="Manager Démo",
            club_id=kadutu.id,
        )
        db.add(club_manager)

        postes = [PosteJoueur.GARDIEN, PosteJoueur.DEFENSEUR, PosteJoueur.MILIEU, PosteJoueur.ATTAQUANT]
        joueurs_par_club: dict[int, list[Joueur]] = {}
        for club, prefix in (
            (kadutu, "Kadutu"),
            (ibanda, "Ibanda"),
            (bagira, "Bagira"),
            (uvira, "Uvira"),
        ):
            js = []
            for i, poste in enumerate(postes, start=1):
                js.append(
                    Joueur(
                        nom_complet=f"Démo {prefix} {i}",
                        date_naissance=date(1997, i, 10 + i),
                        poste=poste,
                        club_actuel_id=club.id,
                    )
                )
            joueurs_par_club[club.id] = js
            db.add_all(js)
        await db.flush()

        now = datetime.now(timezone.utc)

        def match_valide(journee, jours_ago, dom, ext, sd, se, stade):
            return Match(
                saison_id=saison.id,
                journee=journee,
                date_heure=now - timedelta(days=jours_ago),
                stade=stade,
                equipe_domicile_id=dom.id,
                equipe_exterieur_id=ext.id,
                score_domicile=sd,
                score_exterieur=se,
                statut=StatutMatch.VALIDE,
                locked=True,
                valide_par=organisateur.id,
                date_validation=now - timedelta(days=jours_ago - 1),
            )

        m1 = match_valide("J1", 21, kadutu, ibanda, 2, 1, kadutu.stade)
        m2 = match_valide("J1", 21, bagira, uvira, 0, 0, bagira.stade)
        m3 = match_valide("J2", 14, kadutu, bagira, 1, 0, kadutu.stade)
        m4 = match_valide("J2", 14, ibanda, uvira, 3, 1, ibanda.stade)
        m5 = match_valide("J3", 7, kadutu, uvira, 2, 2, kadutu.stade)
        m6 = match_valide("J3", 7, ibanda, bagira, 0, 1, ibanda.stade)
        db.add_all([m1, m2, m3, m4, m5, m6])
        await db.flush()

        # Match terminé, événements encore en attente → file de validation organisateur
        match_attente = Match(
            saison_id=saison.id,
            journee="J4",
            date_heure=now - timedelta(hours=6),
            stade=bagira.stade,
            equipe_domicile_id=bagira.id,
            equipe_exterieur_id=kadutu.id,
            score_domicile=0,
            score_exterieur=0,
            statut=StatutMatch.TERMINE,
            locked=False,
        )
        db.add(match_attente)
        await db.flush()

        buteur = joueurs_par_club[bagira.id][3]  # attaquant
        db.add(
            EvenementMatch(
                match_id=match_attente.id,
                minute=37,
                type=TypeEvenement.BUT,
                joueur_id=buteur.id,
                equipe_concernee=EquipeConcernee.DOMICILE,
                statut_validation=StatutValidationEvenement.EN_ATTENTE,
                source="collecteur_mobile",
                temp_id=uuid.uuid4(),
                cree_par_id=collecteur.id,
            )
        )

        # Match à venir → collecteur
        db.add(
            Match(
                saison_id=saison.id,
                journee="J5",
                date_heure=now + timedelta(days=2),
                stade=uvira.stade,
                equipe_domicile_id=uvira.id,
                equipe_exterieur_id=ibanda.id,
                statut=StatutMatch.PROGRAMME,
            )
        )

        await db.commit()
        print(f"Données DEMO créées : compétition '{DEMO_COMPETITION_NOM}' (id={competition.id}).")
        print(f"Saison id={saison.id} — 6 matchs publiés + 1 en attente de validation + 1 programmé.")
        print(f"Comptes (mot de passe : {DEMO_PASSWORD}) :")
        print("  admin@demo.kivufoot.local")
        print("  organisateur@demo.kivufoot.local")
        print("  club-manager@demo.kivufoot.local")
        print("  collecteur@demo.kivufoot.local")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
