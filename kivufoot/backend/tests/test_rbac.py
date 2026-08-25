import pytest
from fastapi import HTTPException

from app.auth.rbac import verifier_organisateur_de_competition, verifier_scope_club
from app.models.enums import RoleUtilisateur
from tests.factories import creer_club, creer_competition_avec_saison, creer_utilisateur

pytestmark = pytest.mark.asyncio


async def test_organisateur_ne_peut_pas_valider_une_competition_qui_n_est_pas_la_sienne(db_session):
    organisateur_a = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.a@test.local")
    organisateur_b = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.b@test.local")
    competition, _ = await creer_competition_avec_saison(db_session, organisateur_a)
    await db_session.flush()

    # organisateur_a est bien organisateur de sa compétition
    await verifier_organisateur_de_competition(competition.id, organisateur_a, db_session)

    # organisateur_b ne l'est pas -> 403
    with pytest.raises(HTTPException) as exc_info:
        await verifier_organisateur_de_competition(competition.id, organisateur_b, db_session)
    assert exc_info.value.status_code == 403


async def test_admin_peut_toujours_agir_sur_toute_competition(db_session):
    admin = await creer_utilisateur(db_session, RoleUtilisateur.ADMIN, "admin.rbac@test.local")
    organisateur = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.rbac@test.local")
    competition, _ = await creer_competition_avec_saison(db_session, organisateur)
    await db_session.flush()

    await verifier_organisateur_de_competition(competition.id, admin, db_session)  # ne lève rien


async def test_club_manager_ne_gere_que_son_club(db_session):
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    manager_a = await creer_utilisateur(db_session, RoleUtilisateur.CLUB_MANAGER, "manager.a@test.local", club_id=club_a.id)
    await db_session.flush()

    verifier_scope_club(manager_a, club_a.id)  # ne lève rien

    with pytest.raises(HTTPException) as exc_info:
        verifier_scope_club(manager_a, club_b.id)
    assert exc_info.value.status_code == 403
