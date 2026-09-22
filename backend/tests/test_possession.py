"""Scénarios d'acceptation de Possession V1.

Ces tests ne créent aucune donnée sportive de production et n'utilisent pas
les événements du match pour calculer la possession.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.club import Club
from app.models.competition import Competition, Saison
from app.models.enums import EtatPossession, PeriodeMatch, RoleUtilisateur, StatutMatch, StatutPossession, TypeCompetition
from app.models.match import Match
from app.models.user import User
from app.services.possession import (
    get_possession,
    officialiser_possession,
    snapshot_possession,
    snapshot_public_possession,
    suspendre_possession,
    transition_possession,
)


async def contexte(db_session, *, statut=StatutMatch.EN_COURS):
    competition = Competition(nom="Test possession", type=TypeCompetition.TOURNOI)
    saison = Saison(nom="Test", competition=competition)
    domicile = Club(nom="Équipe A", ville="Bukavu")
    exterieur = Club(nom="Équipe B", ville="Bukavu")
    collecteur = User(
        email=f"collecteur-{uuid.uuid4()}@test.invalid",
        mot_de_passe_hash="hash-test",
        role=RoleUtilisateur.COLLECTEUR,
        nom_complet="Collecteur test",
    )
    match = Match(
        saison=saison,
        date_heure=datetime(2026, 9, 22, 12, tzinfo=timezone.utc),
        equipe_domicile=domicile,
        equipe_exterieur=exterieur,
        statut=statut,
        periode=PeriodeMatch.PREMIERE,
    )
    db_session.add_all([competition, saison, domicile, exterieur, collecteur, match])
    await db_session.flush()
    return match, collecteur


def instant(secondes: int) -> datetime:
    return datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc) + timedelta(seconds=secondes)


def operation() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_01_sequences_a_b_a_conservent_les_intervalles(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, EtatPossession.TEAM_A, user.id, operation(), now=instant(0))
    await transition_possession(db_session, match.id, EtatPossession.TEAM_B, user.id, operation(), now=instant(10))
    await transition_possession(db_session, match.id, EtatPossession.TEAM_A, user.id, operation(), now=instant(20))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, EtatPossession.FINISHED, user.id, operation(), now=instant(30))
    possession = await get_possession(db_session, match.id)
    assert (possession.temps_a_ms, possession.temps_b_ms) == (20_000, 10_000)
    assert possession.nombre_changements == 2
    assert (possession.nombre_sequences_a, possession.nombre_sequences_b) == (2, 1)
    detail = await snapshot_possession(db_session, match, possession, now=instant(30))
    assert [x.etat for x in detail.intervalles] == [EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.TEAM_A]


@pytest.mark.asyncio
async def test_02_pause_arrete_le_compteur_equipe(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(0))
    await transition_possession(db_session, match.id, "PAUSE", user.id, operation(), now=instant(10))
    await transition_possession(db_session, match.id, "TEAM_B", user.id, operation(), now=instant(20))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, "FINISHED", user.id, operation(), now=instant(30))
    possession = await get_possession(db_session, match.id)
    assert possession.temps_a_ms == 10_000
    assert possession.temps_b_ms == 10_000
    assert possession.temps_non_attribue_ms == 10_000


@pytest.mark.asyncio
async def test_03_mi_temps_suspend_et_reprise_explicite(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(0))
    match.periode = PeriodeMatch.MI_TEMPS
    await suspendre_possession(db_session, match.id, user.id, now=instant(10))
    possession = await get_possession(db_session, match.id)
    assert possession.etat_courant == EtatPossession.PAUSE
    match.periode = PeriodeMatch.SECONDE
    await transition_possession(db_session, match.id, "TEAM_B", user.id, operation(), now=instant(20))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, "FINISHED", user.id, operation(), now=instant(30))
    assert (possession.temps_a_ms, possession.temps_b_ms, possession.temps_non_attribue_ms) == (10_000, 10_000, 0)


@pytest.mark.asyncio
async def test_04_temps_non_attribue_30_20_10_reste_hors_denomenateur(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(0))
    await transition_possession(db_session, match.id, "PAUSE", user.id, operation(), now=instant(30))
    await transition_possession(db_session, match.id, "TEAM_B", user.id, operation(), now=instant(40))
    await transition_possession(db_session, match.id, "PAUSE", user.id, operation(), now=instant(60))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, "FINISHED", user.id, operation(), now=instant(70))
    possession = await get_possession(db_session, match.id)
    assert (possession.temps_a_ms, possession.temps_b_ms, possession.temps_non_attribue_ms) == (30_000, 20_000, 10_000)
    detail = await snapshot_possession(db_session, match, possession, now=instant(70))
    assert (detail.pourcentage_a, detail.pourcentage_b) == (60, 40)


@pytest.mark.asyncio
async def test_05_absence_de_capture_retourne_non_disponible(db_session):
    match, _ = await contexte(db_session)
    detail = await snapshot_possession(db_session, match, None, now=instant(0))
    public = await snapshot_public_possession(db_session, match, None)
    assert detail.message == "Possession non disponible"
    assert detail.pourcentage_a is None and detail.pourcentage_b is None
    assert public.disponible is False
    assert public.message == "Possession non disponible"


@pytest.mark.asyncio
async def test_06_double_commande_idempotente_sans_double_chronometre(db_session):
    match, user = await contexte(db_session)
    op = operation()
    await transition_possession(db_session, match.id, "TEAM_A", user.id, op, now=instant(0))
    await transition_possession(db_session, match.id, "TEAM_A", user.id, op, now=instant(10))
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(10))
    possession = await get_possession(db_session, match.id)
    detail = await snapshot_possession(db_session, match, possession, now=instant(20))
    assert len(detail.intervalles) == 1
    assert detail.temps_a_ms == 20_000
    assert possession.nombre_sequences_a == 1


@pytest.mark.asyncio
async def test_07_duree_negative_refusee(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(10))
    with pytest.raises(HTTPException) as erreur:
        await transition_possession(db_session, match.id, "TEAM_B", user.id, operation(), now=instant(9))
    assert erreur.value.status_code == 409


@pytest.mark.asyncio
async def test_08_finished_interdit_toute_nouvelle_sequence(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(0))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, "FINISHED", user.id, operation(), now=instant(10))
    with pytest.raises(HTTPException) as erreur:
        await transition_possession(db_session, match.id, "TEAM_B", user.id, operation(), now=instant(20))
    assert erreur.value.status_code in (403, 409)


@pytest.mark.asyncio
async def test_09_publication_exige_match_valide_et_capture_officielle(db_session):
    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(0))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, "FINISHED", user.id, operation(), now=instant(10))
    public_avant = await snapshot_public_possession(db_session, match, await get_possession(db_session, match.id))
    assert public_avant.disponible is False
    match.statut = StatutMatch.VALIDE
    await officialiser_possession(db_session, match.id, user.id)
    public_apres = await snapshot_public_possession(db_session, match, await get_possession(db_session, match.id))
    assert public_apres.disponible is True
    assert public_apres.pourcentage_a == 100


@pytest.mark.asyncio
async def test_10_collecteur_peut_saisir_mais_ne_peut_pas_valider(client, db_session):
    match, user = await contexte(db_session)

    async def utilisateur_courant():
        return user

    app.dependency_overrides[get_current_user] = utilisateur_courant
    response = await client.post(
        f"/api/v1/matchs/{match.id}/possession/transition",
        json={"operation_id": str(operation()), "etat": "TEAM_A"},
    )
    assert response.status_code == 200
    refus = await client.post(f"/api/v1/matchs/{match.id}/valider")
    assert refus.status_code == 403


@pytest.mark.asyncio
async def test_11_correction_organisateur_conserve_une_trace(db_session):
    from app.services.possession import corriger_intervalle_possession

    match, user = await contexte(db_session)
    await transition_possession(db_session, match.id, "TEAM_A", user.id, operation(), now=instant(0))
    await transition_possession(db_session, match.id, "TEAM_B", user.id, operation(), now=instant(10))
    match.statut = StatutMatch.TERMINE
    await transition_possession(db_session, match.id, "FINISHED", user.id, operation(), now=instant(20))
    possession = await get_possession(db_session, match.id)
    detail = await snapshot_possession(db_session, match, possession, now=instant(20))
    intervalle_a = detail.intervalles[0]
    corrige = await corriger_intervalle_possession(
        db_session,
        match.id,
        intervalle_a.id,
        "PAUSE",
        user.id,
        operation(),
        "Le contrôle était incertain sur cette séquence.",
    )
    assert corrige.temps_a_ms == 0
    assert corrige.temps_non_attribue_ms == 10_000
