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


async def test_audit_reserve_a_ladmin(client, db_session):
    token_orga = await _login(client, db_session, RoleUtilisateur.ORGANISATEUR, "orga.audit@test.local")
    refuse = await client.get("/api/v1/audit", headers=_h(token_orga))
    assert refuse.status_code == 403

    token_admin = await _login(client, db_session, RoleUtilisateur.ADMIN, "admin.audit@test.local")
    ok = await client.get("/api/v1/audit", headers=_h(token_admin))
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)


async def test_collecteur_ne_voit_pas_laudit(client, db_session):
    token = await _login(client, db_session, RoleUtilisateur.COLLECTEUR, "col.audit@test.local")
    resp = await client.get("/api/v1/audit", headers=_h(token))
    assert resp.status_code == 403


async def test_admin_approuve_une_proposition(client, db_session):
    club = await creer_club(db_session, "Club Admin")
    joueur = await creer_joueur(db_session, club.id, "Nom Ancien")
    token_club = await _login(
        client, db_session, RoleUtilisateur.CLUB_MANAGER, "manager.prop@test.local", club_id=club.id
    )
    prop = await client.post(
        f"/api/v1/joueurs/{joueur.id}/proposer-modification",
        json={"champ": "nom_complet", "nouvelle_valeur": "Nom Nouveau"},
        headers=_h(token_club),
    )
    assert prop.status_code == 201, prop.text
    pid = prop.json()["id"]

    token_admin = await _login(client, db_session, RoleUtilisateur.ADMIN, "admin.prop@test.local")
    ok = await client.put(f"/api/v1/joueurs/propositions/{pid}/approuver", headers=_h(token_admin))
    assert ok.status_code == 200, ok.text
    assert ok.json()["statut"] == "approuvee"

    detail = await client.get(f"/api/v1/joueurs/{joueur.id}/detail", headers=_h(token_admin))
    assert detail.status_code == 200
    assert detail.json()["nom_complet"] == "Nom Nouveau"


async def test_orga_ne_peut_pas_fusionner(client, db_session):
    club = await creer_club(db_session, "Club Fusion")
    a = await creer_joueur(db_session, club.id, "Maître")
    b = await creer_joueur(db_session, club.id, "Esclave")
    token = await _login(client, db_session, RoleUtilisateur.ORGANISATEUR, "orga.merge@test.local")
    resp = await client.post(
        "/api/v1/joueurs/merge",
        json={"joueur_maitre_id": a.id, "joueur_esclave_id": b.id},
        headers=_h(token),
    )
    assert resp.status_code == 403
