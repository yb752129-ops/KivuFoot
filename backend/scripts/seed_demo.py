"""
Données de DÉMONSTRATION, clairement identifiées (est_demo=True).
Idempotent : relancer ne duplique pas la compétition.
Relancer répare les comptes démo (collecteur, club, coach, orga, admin).

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

DEMO_COMPTES = (
    ("admin.demo@example.com", RoleUtilisateur.ADMIN, "Admin Démo"),
    ("orga.demo@example.com", RoleUtilisateur.ORGANISATEUR, "Organisateur Démo"),
    ("collecteur.demo@example.com", RoleUtilisateur.COLLECTEUR, "Collecteur Démo"),
    ("manager.demo@example.com", RoleUtilisateur.CLUB_MANAGER, "Manager Démo"),
    ("coach.demo@example.com", RoleUtilisateur.COACH, "Coach Démo"),
)


async def ensure_demo_comptes(db) -> None:
    """Crée ou répare les comptes démo. Ne touche pas aux autres utilisateurs."""
    kadutu = (
        await db.execute(select(Club).where(Club.nom == "DEMO FC Kadutu"))
    ).scalar_one_or_none()
    hash_demo = hash_password(DEMO_PASSWORD)
    users = {}
    for email, role, nom in DEMO_COMPTES:
        row = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if row is None:
            row = User(
                email=email,
                mot_de_passe_hash=hash_demo,
                role=role,
                nom_complet=nom,
                est_actif=True,
            )
            db.add(row)
            await db.flush()
        else:
            row.role = role
            row.nom_complet = nom
            row.est_actif = True
            row.mot_de_passe_hash = hash_demo
        if role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH) and kadutu is not None:
            row.club_id = kadutu.id
        users[email] = row
    await db.flush()
    orga = users["orga.demo@example.com"]
    competition = (
        await db.execute(select(Competition).where(Competition.nom == DEMO_COMPETITION_NOM))
    ).scalar_one_or_none()
    if competition is not None:
        lien = (
            await db.execute(
                select(OrganisateurCompetition).where(
                    OrganisateurCompetition.user_id == orga.id,
                    OrganisateurCompetition.competition_id == competition.id,
                )
            )
        ).scalar_one_or_none()
        if lien is None:
            db.add(OrganisateurCompetition(user_id=orga.id, competition_id=competition.id))
    await db.commit()
    print(f"Comptes démo (mot de passe : {DEMO_PASSWORD}) :")
    print("  Organisateur  orga.demo@example.com        → /orga")
    print("  Collecteur    collecteur.demo@example.com  → /collecteur")
    print("  Club          manager.demo@example.com     → /club")
    print("  Coach         coach.demo@example.com       → /coach")
    print("  Admin         admin.demo@example.com       → /admin")


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Competition).where(Competition.nom == DEMO_COMPETITION_NOM))
        if existing.scalar_one_or_none() is not None:
            print("Les données DEMO existent déjà — on répare seulement les comptes.")
            await ensure_demo_comptes(db)
            return

        competition = Competition(
            nom=DEMO_COMPETITION_NOM,
            type=TypeCompetition.CHAMPIONNAT,
            saison_label="2026-DEMO",
            est_demo=True,
        )
        db.add(competition)
        await db.flush()

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

        buteur = joueurs_par_club[bagira.id][3]
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
            )
        )

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
        await ensure_demo_comptes(db)


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
