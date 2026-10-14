import uuid

import pytest

from app.models.actualite import HommeMatch
from app.models.enums import (
    EquipeConcernee,
    StatutMatch,
    StatutParticipation,
    StatutValidationEvenement,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.match import MatchParticipation
from app.models.stats import StatistiqueJoueur
from tests.factories import creer_club, creer_competition_avec_saison, creer_joueur, creer_match

pytestmark = pytest.mark.asyncio


async def _contexte_joueur(db_session):
    _, saison = await creer_competition_avec_saison(db_session)
    club_dom = await creer_club(db_session, "Stats A")
    club_ext = await creer_club(db_session, "Stats B")
    joueur = await creer_joueur(db_session, club_dom.id, "Joueur Stats")
    return saison, club_dom, club_ext, joueur


async def test_historique_public_ne_publie_pas_un_match_sans_trace_joueur(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match_sans_trace = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match_sans_trace.statut = StatutMatch.VALIDE
    match_evenement_refuse = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match_evenement_refuse.statut = StatutMatch.VALIDE
    match_evenement_valide = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match_evenement_valide.statut = StatutMatch.VALIDE

    db_session.add_all(
        [
            EvenementMatch(
                match_id=match_evenement_refuse.id,
                minute=12,
                type=TypeEvenement.BUT,
                joueur_id=joueur.id,
                equipe_concernee=EquipeConcernee.DOMICILE,
                statut_validation=StatutValidationEvenement.VALIDE,
                locked=True,
                refuse=True,
                motif_refus="hors_jeu",
                temp_id=uuid.uuid4(),
            ),
            EvenementMatch(
                match_id=match_evenement_valide.id,
                minute=25,
                type=TypeEvenement.BUT,
                joueur_id=joueur.id,
                equipe_concernee=EquipeConcernee.DOMICILE,
                statut_validation=StatutValidationEvenement.VALIDE,
                locked=True,
                refuse=False,
                temp_id=uuid.uuid4(),
            ),
        ]
    )
    await db_session.flush()

    response = await client.get(f"/api/v1/stats/joueur/{joueur.id}/public/matchs?saison_id={saison.id}")

    assert response.status_code == 200
    payload = response.json()
    assert {ligne["match_id"] for ligne in payload["matchs"]} == {match_evenement_valide.id}
    assert payload["matchs"][0]["statistiques"]["buts"] == 1

    stats_response = await client.get(
        f"/api/v1/stats/joueur/{joueur.id}/public?saison_id={saison.id}"
    )
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["buts"] == 1
    assert stats_payload["matchs_joues"] is None
    assert stats_payload["minutes_jouees"] is None
    assert stats_payload["passes_decisives"] is None

    top_response = await client.get(f"/api/v1/stats/meilleurs-buteurs?saison_id={saison.id}")
    assert top_response.status_code == 200
    assert top_response.json()[0]["joueur_id"] == joueur.id
    assert top_response.json()[0]["valeur"] == 1


async def test_stats_public_ne_transforme_pas_un_evenement_refuse_en_statistique(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE
    db_session.add(
        EvenementMatch(
            match_id=match.id,
            minute=31,
            type=TypeEvenement.BUT,
            joueur_id=joueur.id,
            equipe_concernee=EquipeConcernee.DOMICILE,
            statut_validation=StatutValidationEvenement.VALIDE,
            locked=True,
            refuse=True,
            motif_refus="hors_jeu",
            temp_id=uuid.uuid4(),
        )
    )
    await db_session.flush()

    response = await client.get(f"/api/v1/stats/joueur/{joueur.id}/public?saison_id={saison.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["disponible"] is False
    assert payload["buts"] is None
    assert payload["matchs_joues"] is None
    assert payload["minutes_jouees"] is None
    assert payload["statuts"]["buts"] == "NON_DISPONIBLE"


async def test_top_buteurs_public_exclut_un_evenement_refuse(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE
    db_session.add(
        EvenementMatch(
            match_id=match.id,
            minute=44,
            type=TypeEvenement.BUT,
            joueur_id=joueur.id,
            equipe_concernee=EquipeConcernee.DOMICILE,
            statut_validation=StatutValidationEvenement.VALIDE,
            locked=True,
            refuse=True,
            motif_refus="hors_jeu",
            temp_id=uuid.uuid4(),
        )
    )
    await db_session.flush()

    response = await client.get(f"/api/v1/stats/meilleurs-buteurs?saison_id={saison.id}")

    assert response.status_code == 200
    assert response.json() == []


async def test_stats_public_ignore_un_agregat_qui_contredirait_un_refus(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE
    db_session.add_all(
        [
            MatchParticipation(
                match_id=match.id,
                joueur_id=joueur.id,
                club_id=club_dom.id,
                equipe_concernee=EquipeConcernee.DOMICILE,
                statut=StatutParticipation.TITULAIRE,
                minute_entree=0,
                minute_sortie=90,
            ),
            StatistiqueJoueur(
                joueur_id=joueur.id,
                competition_id=saison.competition_id,
                saison_id=saison.id,
                buts=7,
            ),
            EvenementMatch(
                match_id=match.id,
                minute=44,
                type=TypeEvenement.BUT,
                joueur_id=joueur.id,
                equipe_concernee=EquipeConcernee.DOMICILE,
                statut_validation=StatutValidationEvenement.VALIDE,
                locked=True,
                refuse=True,
                motif_refus="hors_jeu",
                temp_id=uuid.uuid4(),
            ),
        ]
    )
    await db_session.flush()

    response = await client.get(
        f"/api/v1/stats/joueur/{joueur.id}/public?saison_id={saison.id}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matchs_joues"] == 1
    assert payload["buts"] == 0
    assert payload["minutes_jouees"] == 90


async def test_historique_public_accepte_une_designation_homme_du_match_officielle(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE
    db_session.add(HommeMatch(match_id=match.id, joueur_id=joueur.id, club_id=club_dom.id))
    await db_session.flush()

    response = await client.get(f"/api/v1/stats/joueur/{joueur.id}/public/matchs?saison_id={saison.id}")

    assert response.status_code == 200
    payload = response.json()
    assert [ligne["match_id"] for ligne in payload["matchs"]] == [match.id]
    ligne = payload["matchs"][0]
    assert ligne["participation"]["disponible"] is False
    assert ligne["participation"]["minutes"] is None
    assert ligne["homme_du_match"] is True
    assert ligne["statistiques"]["buts"] is None


async def test_stats_public_confirme_participation_et_minutes_sans_agregat(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE
    db_session.add(
        MatchParticipation(
            match_id=match.id,
            joueur_id=joueur.id,
            club_id=club_dom.id,
            equipe_concernee=EquipeConcernee.DOMICILE,
            statut=StatutParticipation.TITULAIRE,
            minute_entree=0,
            minute_sortie=78,
        )
    )
    await db_session.flush()

    response = await client.get(f"/api/v1/stats/joueur/{joueur.id}/public?saison_id={saison.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["disponible"] is True
    assert payload["matchs_joues"] == 1
    assert payload["titularisations"] == 1
    assert payload["minutes_jouees"] == 78
    assert payload["buts"] == 0
    assert payload["statuts"]["minutes_jouees"] == "CONFIRMEE"


async def test_stats_public_ne_fabrique_pas_90_minutes(client, db_session):
    saison, club_dom, club_ext, joueur = await _contexte_joueur(db_session)
    match = await creer_match(db_session, saison.id, club_dom.id, club_ext.id)
    match.statut = StatutMatch.VALIDE
    db_session.add(
        MatchParticipation(
            match_id=match.id,
            joueur_id=joueur.id,
            club_id=club_dom.id,
            equipe_concernee=EquipeConcernee.DOMICILE,
            statut=StatutParticipation.TITULAIRE,
            # Une feuille de match existe, mais aucune borne de minutes n'a
            # été collectée : l'API doit garder la valeur à null.
            minute_entree=0,
            minute_sortie=None,
        )
    )
    await db_session.flush()

    stats_response = await client.get(
        f"/api/v1/stats/joueur/{joueur.id}/public?saison_id={saison.id}"
    )
    history_response = await client.get(
        f"/api/v1/stats/joueur/{joueur.id}/public/matchs?saison_id={saison.id}"
    )

    assert stats_response.status_code == 200
    assert stats_response.json()["minutes_jouees"] is None
    assert stats_response.json()["statuts"]["minutes_jouees"] == "NON_DISPONIBLE"
    assert history_response.status_code == 200
    assert history_response.json()["matchs"][0]["participation"]["minutes"] is None
