import pytest

from tests.factories import creer_utilisateur
from app.models.enums import RoleUtilisateur

pytestmark = pytest.mark.asyncio


async def test_login_puis_acces_route_protegee(client, db_session):
    await creer_utilisateur(db_session, RoleUtilisateur.ADMIN, "admin.test@kivufoot.local")
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.test@kivufoot.local", "mot_de_passe": "TestPassword123!"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    resp_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert resp_me.status_code == 200
    assert resp_me.json()["email"] == "admin.test@kivufoot.local"


async def test_login_mauvais_mot_de_passe_refuse(client, db_session):
    await creer_utilisateur(db_session, RoleUtilisateur.ADMIN, "admin2.test@kivufoot.local")
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin2.test@kivufoot.local", "mot_de_passe": "MauvaisMotDePasse"},
    )
    assert resp.status_code == 401


async def test_logout_revoque_le_refresh_token(client, db_session):
    await creer_utilisateur(db_session, RoleUtilisateur.ADMIN, "admin3.test@kivufoot.local")
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin3.test@kivufoot.local", "mot_de_passe": "TestPassword123!"},
    )
    tokens = resp.json()

    resp_logout = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resp_logout.status_code == 204

    resp_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp_refresh.status_code == 401  # le refresh token révoqué ne fonctionne plus


async def test_route_protegee_sans_token_refusee(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_register_supporter_puis_me(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "nom_complet": "Yves Test",
            "email": "yves.supporter@example.com",
            "mot_de_passe": "MotDePasse123",
        },
    )
    assert resp.status_code == 201
    tokens = resp.json()
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "yves.supporter@example.com"
    assert body["role"] == "supporter"
    assert body["nom_complet"] == "Yves Test"


async def test_register_email_deja_pris(client):
    payload = {
        "nom_complet": "Yves Test",
        "email": "yves.dup@example.com",
        "mot_de_passe": "MotDePasse123",
    }
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
