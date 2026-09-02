import uuid

import pytest

from app.models.enums import EquipeConcernee, StatutMatch, StatutValidationEvenement, TypeEvenement
from app.schemas.evenement import EvenementCreate
from app.services.sync_offline import pousser_evenement
from app.services.validation import valider_match
from tests.factories import creer_club, creer_competition_avec_saison, creer_joueur, creer_match, creer_utilisateur
from app.models.enums import RoleUtilisateur

pytestmark = pytest.mark.asyncio


async def test_push_idempotent_meme_temp_id_ne_duplique_pas(db_session):
    organisateur = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga2@test.local")
    collecteur = await creer_utilisateur(db_session, RoleUtilisateur.COLLECTEUR, "collecteur@test.local")
    _, saison = await creer_competition_avec_saison(db_session, organisateur)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    joueur = await creer_joueur(db_session, club_a.id)
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    await db_session.flush()

    temp_id = uuid.uuid4()
    ev = EvenementCreate(
        temp_id=temp_id, minute=5, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
    )

    resultat_1 = await pousser_evenement(db_session, match_.id, ev, collecteur.id)
    await db_session.flush()
    resultat_2 = await pousser_evenement(db_session, match_.id, ev, collecteur.id)  # retry réseau simulé
    await db_session.flush()

    assert resultat_1.evenement_id == resultat_2.evenement_id  # pas de duplication

    from sqlalchemy import select, func
    from app.models.evenement import EvenementMatch
    count = (await db_session.execute(
        select(func.count()).select_from(EvenementMatch).where(EvenementMatch.temp_id == temp_id)
    )).scalar_one()
    assert count == 1


async def test_push_sur_match_verrouille_rejette_automatiquement(db_session):
    organisateur = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga3@test.local")
    collecteur = await creer_utilisateur(db_session, RoleUtilisateur.COLLECTEUR, "collecteur2@test.local")
    _, saison = await creer_competition_avec_saison(db_session, organisateur)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    joueur = await creer_joueur(db_session, club_a.id)
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    await db_session.flush()

    await valider_match(db_session, match_.id, organisateur.id)
    await db_session.flush()
    assert match_.locked is True

    ev = EvenementCreate(
        temp_id=uuid.uuid4(), minute=91, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
    )
    resultat = await pousser_evenement(db_session, match_.id, ev, collecteur.id)
    await db_session.flush()

    from app.models.evenement import EvenementMatch
    evenement = await db_session.get(EvenementMatch, resultat.evenement_id)
    assert evenement.statut_validation == StatutValidationEvenement.REJETE
    assert "verrouillé" in evenement.commentaire_rejet.lower()


async def test_conflit_detecte_entre_deux_collecteurs(db_session):
    organisateur = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga4@test.local")
    collecteur_1 = await creer_utilisateur(db_session, RoleUtilisateur.COLLECTEUR, "c1@test.local")
    collecteur_2 = await creer_utilisateur(db_session, RoleUtilisateur.COLLECTEUR, "c2@test.local")
    _, saison = await creer_competition_avec_saison(db_session, organisateur)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    joueur = await creer_joueur(db_session, club_a.id)
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    await db_session.flush()

    ev1 = EvenementCreate(
        temp_id=uuid.uuid4(), minute=20, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
    )
    ev2 = EvenementCreate(
        temp_id=uuid.uuid4(), minute=20, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
    )

    await pousser_evenement(db_session, match_.id, ev1, collecteur_1.id)
    await db_session.flush()
    resultat_2 = await pousser_evenement(db_session, match_.id, ev2, collecteur_2.id)
    await db_session.flush()

    from app.models.evenement import EvenementMatch
    ev2_db = await db_session.get(EvenementMatch, resultat_2.evenement_id)
    assert ev2_db.conflit is True
