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


def _positions(formation):
    lignes = [1, *[int(nombre) for nombre in formation.split("-")]]
    return [(ligne_index, position_index) for ligne_index, places in enumerate(lignes) for position_index in range(places)]


def _payload(formation, joueurs, order=None, positions=None):
    ordre = order or list(range(len(joueurs)))
    position_map = positions or _positions(formation)
    return {
        "equipe": "domicile",
        "formation": formation,
        "joueurs": [
            {
                "joueur_id": joueurs[index].id,
                "statut": "titulaire",
                "numero": index + 1,
                "ligne_index": position_map[index][0],
                "position_index": position_map[index][1],
            }
            for index in ordre
        ],
    }


async def _contexte(db_session, client):
    club_a = await creer_club(db_session, "Club Positions")
    club_b = await creer_club(db_session, "Club Positions Adverse")
    joueurs = [await creer_joueur(db_session, club_a.id, f"Joueur Position {index}") for index in range(11)]
    orga = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.positions@test.example")
    _, saison = await creer_competition_avec_saison(db_session, orga)
    coach = await creer_utilisateur(db_session, RoleUtilisateur.COACH, "coach.positions@test.example", club_id=club_a.id)
    await db_session.commit()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": coach.email, "mot_de_passe": "TestPassword123!"},
    )
    assert response.status_code == 200, response.text
    return club_a, club_b, joueurs, saison, {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_positions_conservees_dans_ordre_desordonne_et_dans_la_lecture(client, db_session):
    club_a, club_b, joueurs, saison, headers = await _contexte(db_session, client)
    ordre_desordre = [0, 7, 8, 1, 2, 3, 4, 5, 9, 10, 6]

    for index, formation in enumerate(("4-2-3-1", "4-3-3", "4-4-2")):
        match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
        payload = _payload(formation, joueurs, order=ordre_desordre)
        response = await client.put(
            f"/api/v1/matchs/{match_.id}/composition",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 200, response.text
        bloc = response.json()["domicile"]
        assert bloc["position_complete"] is True
        positions_lecture = {
            joueur["id"]: (joueur["ligne_index"], joueur["position_index"])
            for joueur in bloc["titulaires"]
        }
        positions_attendues = {
            joueurs[player_index].id: _positions(formation)[player_index]
            for player_index in range(11)
        }
        assert positions_lecture == positions_attendues
        assert len({position for position in positions_lecture.values()}) == 11
        assert index in (0, 1, 2)


async def test_position_absente_ou_doublon_refuse_sans_deplacement(client, db_session):
    club_a, club_b, joueurs, saison, headers = await _contexte(db_session, client)
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)

    doublon = _positions("4-3-3")
    doublon[1] = doublon[0]
    response_doublon = await client.put(
        f"/api/v1/matchs/{match_.id}/composition",
        json=_payload("4-3-3", joueurs, positions=doublon),
        headers=headers,
    )
    assert response_doublon.status_code == 400
    assert "déjà occupée" in response_doublon.json()["detail"]

    position_manquante = _positions("4-3-3")
    payload = _payload("4-3-3", joueurs, positions=position_manquante)
    payload["joueurs"][4]["ligne_index"] = None
    payload["joueurs"][4]["position_index"] = None
    response_manquante = await client.put(
        f"/api/v1/matchs/{match_.id}/composition",
        json=payload,
        headers=headers,
    )
    assert response_manquante.status_code == 400
    assert "position tactique explicite" in response_manquante.json()["detail"]
