import pytest

from app.models.enums import RoleUtilisateur
from tests.factories import (
    creer_club,
    creer_competition_avec_saison,
    creer_joueur,
    creer_match,
    creer_utilisateur,
)

pytestmark = pytest.mark.asyncio


async def _login(client, db, role, email, club_id=None):
    await creer_utilisateur(db, role, email, club_id=club_id)
    await db.commit()
    resp = await client.post("/api/v1/auth/login", json={"email": email, "mot_de_passe": "TestPassword123!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


async def test_coach_pose_sa_composition_pas_celle_de_ladversaire(client, db_session):
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    j_a = await creer_joueur(db_session, club_a.id, "Joueur A")
    j_b = await creer_joueur(db_session, club_b.id, "Joueur B")
    orga = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.coach@test.local")
    _, saison = await creer_competition_avec_saison(db_session, orga)
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    token = await _login(client, db_session, RoleUtilisateur.COACH, "coach.a@test.local", club_id=club_a.id)
    headers = _h(token)

    ok = await client.post(
        f"/api/v1/matchs/{match_.id}/participations",
        json={
            "joueur_id": j_a.id,
            "club_id": club_a.id,
            "equipe_concernee": "domicile",
            "statut": "titulaire",
        },
        headers=headers,
    )
    assert ok.status_code == 201, ok.text
    pid = ok.json()["id"]

    refuse = await client.post(
        f"/api/v1/matchs/{match_.id}/participations",
        json={
            "joueur_id": j_b.id,
            "club_id": club_b.id,
            "equipe_concernee": "exterieur",
            "statut": "titulaire",
        },
        headers=headers,
    )
    assert refuse.status_code == 403

    put = await client.put(
        f"/api/v1/matchs/{match_.id}/participations/{pid}",
        json={"statut": "remplacant"},
        headers=headers,
    )
    assert put.status_code == 200
    assert put.json()["statut"] == "remplacant"

    club = await client.get(f"/api/v1/clubs/{club_a.id}")
    assert club.status_code == 200
    assert club.json()["coach_nom"] == "Test coach"


async def test_coach_ne_peut_pas_saisir_un_fait(client, db_session):
    club_a = await creer_club(db_session, "Club A2")
    club_b = await creer_club(db_session, "Club B2")
    j_a = await creer_joueur(db_session, club_a.id, "Joueur A2")
    orga = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.coach2@test.local")
    _, saison = await creer_competition_avec_saison(db_session, orga)
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    token = await _login(client, db_session, RoleUtilisateur.COACH, "coach.fait@test.local", club_id=club_a.id)
    resp = await client.post(
        f"/api/v1/matchs/{match_.id}/evenements",
        json={
            "temp_id": "11111111-1111-1111-1111-111111111111",
            "minute": 10,
            "type": "but",
            "joueur_id": j_a.id,
            "equipe_concernee": "domicile",
        },
        headers=_h(token),
    )
    assert resp.status_code == 403
