import uuid

import pytest

from app.models.enums import EquipeConcernee, StatutMatch, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from tests.factories import creer_club, creer_competition_avec_saison, creer_match

pytestmark = pytest.mark.asyncio


async def test_evenement_refuse_absent_de_la_vue_publique(client, db_session):
    _, saison = await creer_competition_avec_saison(db_session)
    club_dom = await creer_club(db_session, "Public A")
    club_ext = await creer_club(db_session, "Public B")
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE

    conserve = EvenementMatch(
        match_id=match.id,
        minute=12,
        type=TypeEvenement.CARTON_JAUNE,
        equipe_concernee=EquipeConcernee.DOMICILE,
        statut_validation=StatutValidationEvenement.VALIDE,
        locked=True,
        refuse=False,
        temp_id=uuid.uuid4(),
    )
    refuse = EvenementMatch(
        match_id=match.id,
        minute=18,
        type=TypeEvenement.CARTON_JAUNE,
        equipe_concernee=EquipeConcernee.EXTERIEUR,
        statut_validation=StatutValidationEvenement.VALIDE,
        locked=True,
        refuse=True,
        motif_refus="hors_jeu",
        temp_id=uuid.uuid4(),
    )
    db_session.add_all([conserve, refuse])
    await db_session.flush()

    response = await client.get(f"/api/v1/matchs/{match.id}/evenements-publics")

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [conserve.id]
    assert all(row["refuse"] is False for row in payload)
