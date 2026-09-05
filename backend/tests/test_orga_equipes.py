import pytest

from app.models.enums import RoleUtilisateur
from tests.factories import creer_club, creer_competition_avec_saison, creer_utilisateur

pytestmark = pytest.mark.asyncio


async def _login(client, db, role, email):
    await creer_utilisateur(db, role, email)
    await db.commit()
    resp = await client.post("/api/v1/auth/login", json={"email": email, "mot_de_passe": "TestPassword123!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


async def test_orga_cree_equipe_inscrit_et_programme_un_match(client, db_session):
    token = await _login(client, db_session, RoleUtilisateur.ORGANISATEUR, "orga.equipes@test.local")
    from sqlalchemy import select
    from app.models.user import User

    orga = (await db_session.execute(select(User).where(User.email == "orga.equipes@test.local"))).scalar_one()
    _comp, saison = await creer_competition_avec_saison(db_session, orga, est_demo=False)
    await db_session.commit()
    headers = _h(token)

    r1 = await client.post(
        "/api/v1/clubs",
        json={"nom": "Droit — Promo 2025", "ville": "Mukaza", "stade": "Stade Prince Louis Rwagasore"},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    c1 = r1.json()
    r2 = await client.post(
        "/api/v1/clubs",
        json={"nom": "Médecine — Promo 2024", "ville": "Ntahangwa"},
        headers=headers,
    )
    assert r2.status_code == 201, r2.text
    c2 = r2.json()

    i1 = await client.post(f"/api/v1/saisons/{saison.id}/clubs", json={"club_id": c1["id"]}, headers=headers)
    i2 = await client.post(f"/api/v1/saisons/{saison.id}/clubs", json={"club_id": c2["id"]}, headers=headers)
    assert i1.status_code == 201 and i2.status_code == 201

    listed = await client.get(f"/api/v1/saisons/{saison.id}/clubs")
    assert listed.status_code == 200
    assert {c["id"] for c in listed.json()} == {c1["id"], c2["id"]}

    m = await client.post(
        "/api/v1/matchs",
        json={
            "saison_id": saison.id,
            "journee": "J1",
            "date_heure": "2026-09-19T13:00:00+02:00",
            "stade": "Stade Prince Louis Rwagasore",
            "equipe_domicile_id": c1["id"],
            "equipe_exterieur_id": c2["id"],
        },
        headers=headers,
    )
    assert m.status_code == 201, m.text
    body = m.json()
    assert body["statut"] == "programme"
    assert "2026-09-19" in body["date_heure"]
    assert body["equipe_domicile_id"] == c1["id"]


async def test_match_refuse_equipe_non_inscrite(client, db_session):
    token = await _login(client, db_session, RoleUtilisateur.ORGANISATEUR, "orga.hors@test.local")
    from sqlalchemy import select
    from app.models.user import User

    orga = (await db_session.execute(select(User).where(User.email == "orga.hors@test.local"))).scalar_one()
    _comp, saison = await creer_competition_avec_saison(db_session, orga, est_demo=False)
    club_a = await creer_club(db_session, "Équipe A")
    club_b = await creer_club(db_session, "Équipe B")
    await db_session.commit()

    resp = await client.post(
        "/api/v1/matchs",
        json={
            "saison_id": saison.id,
            "date_heure": "2026-09-19T15:00:00+02:00",
            "equipe_domicile_id": club_a.id,
            "equipe_exterieur_id": club_b.id,
        },
        headers=_h(token),
    )
    assert resp.status_code == 400


async def test_autre_orga_ne_peut_pas_inscrire(client, db_session):
    token_a = await _login(client, db_session, RoleUtilisateur.ORGANISATEUR, "orga.a.insc@test.local")
    token_b = await _login(client, db_session, RoleUtilisateur.ORGANISATEUR, "orga.b.insc@test.local")
    from sqlalchemy import select
    from app.models.user import User

    orga_a = (await db_session.execute(select(User).where(User.email == "orga.a.insc@test.local"))).scalar_one()
    _comp, saison = await creer_competition_avec_saison(db_session, orga_a, est_demo=False)
    club = await creer_club(db_session, "Équipe C")
    await db_session.commit()

    ok = await client.post(
        f"/api/v1/saisons/{saison.id}/clubs", json={"club_id": club.id}, headers=_h(token_a)
    )
    assert ok.status_code == 201
    refuse = await client.post(
        f"/api/v1/saisons/{saison.id}/clubs", json={"club_id": club.id}, headers=_h(token_b)
    )
    assert refuse.status_code in (403, 409)


async def test_supporter_ne_peut_pas_creer_club(client, db_session):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"nom_complet": "Yves Test", "email": "yves.club@example.com", "mot_de_passe": "MotDePasse123"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    cree = await client.post(
        "/api/v1/clubs",
        json={"nom": "Supporter FC", "ville": "Bujumbura"},
        headers=_h(token),
    )
    assert cree.status_code == 403
