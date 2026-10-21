from datetime import datetime, timezone

import pytest

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
    return response.json()["access_token"]


async def test_admin_cree_un_role_club_et_peut_revoquer_son_activation(client, db_session):
    admin_token = await _login(client, db_session, RoleUtilisateur.ADMIN, "admin.club-role@test.example")
    club = await creer_club(db_session, "Club nouveau rôle")
    await db_session.commit()

    created = await client.post(
        "/api/v1/admin/utilisateurs",
        headers=_h(admin_token),
        json={
            "nom_complet": "Compte Club",
            "email": "compte.club-role@test.example",
            "role": "club",
            "club_id": club.id,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["utilisateur"]["role"] == "club"
    assert body["utilisateur"]["activation_en_attente"] is True
    assert body["jeton_activation"]

    user = await db_session.get(User, body["utilisateur"]["id"])
    assert user is not None
    assert user.jeton_activation_hash != body["jeton_activation"]
    assert user.jeton_activation_expire is not None
    delta = user.jeton_activation_expire - datetime.now(timezone.utc)
    assert 71 <= delta.total_seconds() / 3600 <= 72.1

    revoked = await client.post(
        f"/api/v1/admin/utilisateurs/{user.id}/revoquer-activation",
        headers=_h(admin_token),
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["activation_en_attente"] is False
    await db_session.refresh(user)
    assert user.jeton_activation_hash is None
    assert user.jeton_activation_expire is None
