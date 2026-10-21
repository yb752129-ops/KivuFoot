import pytest
from sqlalchemy import select

from app.models.enums import RoleUtilisateur
from app.models.user import User
from tests.factories import creer_club, creer_utilisateur

pytestmark = pytest.mark.asyncio


def _h(token):
    return {"Authorization": f"Bearer {token}"}


async def _login(client, db, role, email, club_id=None):
    await creer_utilisateur(db, role, email, club_id=club_id)
    await db.commit()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "mot_de_passe": "TestPassword123!"},
    )
    assert response.status_code == 200
    return response.json()


async def test_desactivation_revoque_le_refresh_et_invalide_le_compte(client, db_session):
    club = await creer_club(db_session, "Club désactivation")
    admin = await _login(client, db_session, RoleUtilisateur.ADMIN, "admin.disable@test.example")
    account = await _login(
        client,
        db_session,
        RoleUtilisateur.CLUB,
        "club.disable@test.example",
        club_id=club.id,
    )
    user = await db_session.scalar(
        select(User).where(User.email == "club.disable@test.example")
    )
    assert user is not None

    disabled = await client.patch(
        f"/api/v1/admin/utilisateurs/{user.id}",
        headers=_h(admin["access_token"]),
        json={"est_actif": False},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["est_actif"] is False

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": account["refresh_token"]},
    )
    assert refresh.status_code == 401
    access = await client.get("/api/v1/auth/me", headers=_h(account["access_token"]))
    assert access.status_code == 401
