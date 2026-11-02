from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.audit import AuditLog
from app.models.club import Club
from app.models.competition import Competition, Saison, SaisonClub
from app.models.enums import PeriodeMatch, RoleUtilisateur, StatutMatch, TypeCompetition
from app.models.match import Match
from app.models.sport_engine import MatchQualificationSlot
from app.models.user import User
from app.schemas.evenement import EvenementCreate
from app.schemas.match import MatchCreate
from app.schemas.sport_engine import ReglementConfiguration
from app.services.calcul_classement import calculer_classement
from app.services.progression_sportive import (
    etats_sportifs_saison,
    propager_vainqueur_vers_tour_suivant,
    verifier_equipe_directement_nommable,
)
from app.services.regles_temps_match import (
    MODE_PROLONGATIONS_2X15,
    verifier_fin_match,
    verifier_resultat_eliminatoire_validable,
    verifier_tirs_autorises,
    verifier_transition_periode,
    duree_officielle_match_minutes,
)
from tests.sqlite_compat import utiliser_types_sqlite


@pytest_asyncio.fixture
async def db_fictif():
    """Base SQLite jetable, avec uniquement des entités de test fictives."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    tables = [
        Competition.__table__,
        Saison.__table__,
        Club.__table__,
        SaisonClub.__table__,
        User.__table__,
        Match.__table__,
        MatchQualificationSlot.__table__,
        AuditLog.__table__,
    ]
    restore_types = utiliser_types_sqlite(tables)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
        restore_types()


async def creer_edition_fictive(db):
    competition = Competition(
        nom="DEMO - Coupe des Règles Fictives",
        type=TypeCompetition.COUPE,
        est_demo=True,
    )
    db.add(competition)
    await db.flush()
    saison = Saison(competition_id=competition.id, nom="Édition fictive 2042")
    clubs = [
        Club(nom="ASTER-9", ville="Ville fictive"),
        Club(nom="LYNX-8", ville="Ville fictive"),
        Club(nom="COMETE-7", ville="Ville fictive"),
        Club(nom="NEBULA-6", ville="Ville fictive"),
    ]
    auteur = User(
        email="fixture-author@example.invalid",
        mot_de_passe_hash="not-a-real-password-hash",
        role=RoleUtilisateur.ADMIN,
        nom_complet="Auteur fictif des tests",
    )
    db.add_all([saison, *clubs, auteur])
    await db.flush()
    db.add_all(SaisonClub(saison_id=saison.id, club_id=club.id, groupe="A") for club in clubs)
    await db.flush()
    return saison, clubs, auteur


def match_fictif(saison_id, domicile_id, exterieur_id, *, phase="poule", score=(0, 0), statut=StatutMatch.VALIDE, **extra):
    return Match(
        saison_id=saison_id,
        date_heure=datetime(2042, 6, 1, 12, 0, tzinfo=timezone.utc),
        equipe_domicile_id=domicile_id,
        equipe_exterieur_id=exterieur_id,
        score_domicile=score[0],
        score_exterieur=score[1],
        statut=statut,
        phase=phase,
        **extra,
    )


def reglement_db(mode=MODE_PROLONGATIONS_2X15):
    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
        configuration={"match": {"mode_egalite_eliminatoire": mode}}
    )))
    return db


def test_match_create_requires_explicit_sources_for_each_knockout_slot():
    fixture = MatchCreate(
        saison_id=7,
        date_heure=datetime(2042, 6, 1, tzinfo=timezone.utc),
        phase="quart",
        source_match_domicile_id=51,
        equipe_exterieur_id=83,
    )
    assert fixture.source_match_domicile_id == 51
    assert fixture.equipe_domicile_id is None
    with pytest.raises(ValidationError):
        MatchCreate(
            saison_id=7,
            date_heure=datetime(2042, 6, 1, tzinfo=timezone.utc),
            phase="poule",
            source_match_domicile_id=51,
            equipe_exterieur_id=83,
        )


def test_official_draw_exception_is_explicit_and_limited_to_named_quarterfinal_teams():
    fixture = MatchCreate(
        saison_id=7,
        date_heure=datetime(2042, 6, 1, tzinfo=timezone.utc),
        phase="quart",
        equipe_domicile_id=81,
        equipe_exterieur_id=83,
        appariement_manuel_officiel=True,
    )
    assert fixture.appariement_manuel_officiel is True

    with pytest.raises(ValidationError):
        MatchCreate(
            saison_id=7,
            date_heure=datetime(2042, 6, 1, tzinfo=timezone.utc),
            phase="quart",
            source_match_domicile_id=51,
            equipe_exterieur_id=83,
            appariement_manuel_officiel=True,
        )

    with pytest.raises(ValidationError):
        MatchCreate(
            saison_id=7,
            date_heure=datetime(2042, 6, 1, tzinfo=timezone.utc),
            phase="demi",
            equipe_domicile_id=81,
            equipe_exterieur_id=83,
            appariement_manuel_officiel=True,
        )


def test_rule_schema_accepts_both_competition_modes_and_preserves_extra_keys():
    direct = ReglementConfiguration.model_validate({
        "match": {"mode_egalite_eliminatoire": "tirs_au_but_apres_90", "note_comite": "fiction"}
    })
    extra_time = ReglementConfiguration.model_validate({
        "match": {"mode_egalite_eliminatoire": "prolongations_2x15"}
    })
    assert direct.match.mode_egalite_eliminatoire == "tirs_au_but_apres_90"
    assert direct.match.note_comite == "fiction"
    assert extra_time.match.mode_egalite_eliminatoire == MODE_PROLONGATIONS_2X15


def test_event_schema_accepts_extra_time_periods_only_as_playing_periods():
    base = {
        "temp_id": uuid.uuid4(),
        "minute": 108,
        "type": "but",
        "joueur_id": 4,
        "equipe_concernee": "domicile",
    }
    event = EvenementCreate(**base, periode="4")
    assert event.periode == "4"
    with pytest.raises(ValidationError):
        EvenementCreate(**base, periode="mi_temps_et")


@pytest.mark.asyncio
async def test_extra_time_transitions_and_finish_gate_follow_the_frozen_rule():
    db = reglement_db()
    match = Match(
        saison_id=1,
        equipe_domicile_id=1,
        equipe_exterieur_id=2,
        phase="quart",
        score_domicile=1,
        score_exterieur=1,
        periode="2",
        reglement_version_id=91,
    )
    await verifier_transition_periode(db, match, PeriodeMatch.PROLONGATION_PREMIERE)
    with pytest.raises(HTTPException) as finish_at_90:
        await verifier_fin_match(db, match)
    assert finish_at_90.value.status_code == 409
    with pytest.raises(HTTPException) as shots_too_early:
        await verifier_tirs_autorises(db, match)
    assert shots_too_early.value.status_code == 409

    match.periode = "3"
    await verifier_transition_periode(db, match, PeriodeMatch.MI_TEMPS_PROLONGATION)
    match.periode = "mi_temps_et"
    await verifier_transition_periode(db, match, PeriodeMatch.PROLONGATION_SECONDE)
    match.periode = "4"
    with pytest.raises(HTTPException) as unresolved_draw:
        await verifier_resultat_eliminatoire_validable(db, match)
    assert unresolved_draw.value.status_code == 409

    match.tirs_au_but = [
        {"ordre": 1, "equipe_concernee": "domicile", "resultat": "marque"},
        {"ordre": 2, "equipe_concernee": "exterieur", "resultat": "rate"},
        {"ordre": 3, "equipe_concernee": "domicile", "resultat": "marque"},
        {"ordre": 4, "equipe_concernee": "exterieur", "resultat": "rate"},
        {"ordre": 5, "equipe_concernee": "domicile", "resultat": "marque"},
        {"ordre": 6, "equipe_concernee": "exterieur", "resultat": "rate"},
        {"ordre": 7, "equipe_concernee": "domicile", "resultat": "marque"},
    ]
    await verifier_resultat_eliminatoire_validable(db, match)
    assert duree_officielle_match_minutes(match) == 120


@pytest.mark.asyncio
async def test_direct_penalties_mode_does_not_allow_extra_time_transitions():
    db = reglement_db("tirs_au_but_apres_90")
    match = Match(
        saison_id=1,
        equipe_domicile_id=1,
        equipe_exterieur_id=2,
        phase="demi",
        score_domicile=0,
        score_exterieur=0,
        periode="2",
        reglement_version_id=92,
    )
    with pytest.raises(HTTPException) as refused:
        await verifier_transition_periode(db, match, PeriodeMatch.PROLONGATION_PREMIERE)
    assert refused.value.status_code == 400
    await verifier_tirs_autorises(db, match)


@pytest.mark.asyncio
async def test_group_table_excludes_knockout_points_and_sports_state_stays_distinct(db_fictif):
    saison, clubs, _ = await creer_edition_fictive(db_fictif)
    aster, lynx, comete, nebula = clubs
    db_fictif.add_all([
        match_fictif(saison.id, aster.id, lynx.id, phase="poule", score=(2, 0)),
        match_fictif(saison.id, aster.id, comete.id, phase="quart", score=(0, 3)),
    ])
    await db_fictif.flush()

    lignes = {row.club_id: row for row in await calculer_classement(db_fictif, saison.id)}
    etats = await etats_sportifs_saison(db_fictif, saison.id)
    assert lignes[aster.id].points == 3
    assert lignes[aster.id].buts_marques == 2
    assert lignes[comete.id].points == 0
    assert lignes[comete.id].matchs_joues == 0
    assert etats[comete.id]["statut_sportif"] == "qualifie"
    assert etats[aster.id]["statut_sportif"] == "elimine"
    statuts_administratifs = (await db_fictif.execute(
        select(SaisonClub.club_id, SaisonClub.statut).where(SaisonClub.saison_id == saison.id)
    )).all()
    assert all(statut == "actif" for _, statut in statuts_administratifs)


@pytest.mark.asyncio
async def test_validation_propagates_only_the_explicit_winner_and_blocks_the_loser(db_fictif):
    saison, clubs, auteur = await creer_edition_fictive(db_fictif)
    aster, lynx, comete, nebula = clubs
    source = match_fictif(saison.id, aster.id, lynx.id, phase="barrage", score=(2, 1))
    cible = match_fictif(
        saison.id,
        None,
        comete.id,
        phase="quart",
        statut=StatutMatch.PROGRAMME,
        score=(0, 0),
    )
    db_fictif.add_all([source, cible])
    await db_fictif.flush()
    db_fictif.add(MatchQualificationSlot(
        match_cible_id=cible.id,
        cote="domicile",
        match_source_id=source.id,
        cree_par_id=auteur.id,
    ))
    await db_fictif.flush()

    await propager_vainqueur_vers_tour_suivant(db_fictif, source, auteur.id)
    await db_fictif.flush()
    assert cible.equipe_domicile_id == aster.id

    with pytest.raises(HTTPException) as automatic_source_required:
        await verifier_equipe_directement_nommable(db_fictif, saison.id, aster.id, "quart")
    assert automatic_source_required.value.status_code == 409
    assert "sélectionnez le vainqueur de son match source" in automatic_source_required.value.detail

    with pytest.raises(HTTPException) as loser_rejected:
        await verifier_equipe_directement_nommable(db_fictif, saison.id, lynx.id, "quart")
    assert loser_rejected.value.status_code == 409
    assert "éliminée" in loser_rejected.value.detail
    assert await db_fictif.scalar(select(AuditLog.id).where(AuditLog.record_id == cible.id)) is not None


@pytest.mark.asyncio
async def test_official_quarterfinal_draw_allows_direct_qualified_teams_only(db_fictif):
    saison, clubs, _ = await creer_edition_fictive(db_fictif)
    aster, lynx, comete, nebula = clubs
    direct = Club(nom="ORBIT-5", ville="Ville fictive")
    non_confirme = Club(nom="PULSAR-6", ville="Ville fictive")
    adversaire_non_confirme = Club(nom="NOVA-7", ville="Ville fictive")
    db_fictif.add_all([direct, non_confirme, adversaire_non_confirme])
    await db_fictif.flush()
    db_fictif.add_all(
        SaisonClub(saison_id=saison.id, club_id=club.id, groupe="A")
        for club in (direct, non_confirme, adversaire_non_confirme)
    )
    barrage_valide = match_fictif(
        saison.id,
        aster.id,
        lynx.id,
        phase="barrage",
        score=(2, 1),
        statut=StatutMatch.VALIDE,
    )
    barrage_qualifie_2 = match_fictif(
        saison.id,
        comete.id,
        nebula.id,
        phase="barrage",
        score=(1, 2),
        statut=StatutMatch.VALIDE,
    )
    barrage_non_valide = match_fictif(
        saison.id,
        non_confirme.id,
        adversaire_non_confirme.id,
        phase="barrage",
        score=(0, 0),
        statut=StatutMatch.PROGRAMME,
    )
    db_fictif.add_all([barrage_valide, barrage_qualifie_2, barrage_non_valide])
    await db_fictif.flush()

    appariement_deux_vainqueurs = MatchCreate(
        saison_id=saison.id,
        date_heure=datetime(2042, 6, 2, tzinfo=timezone.utc),
        phase="quart",
        equipe_domicile_id=aster.id,
        equipe_exterieur_id=nebula.id,
        appariement_manuel_officiel=True,
    )
    assert appariement_deux_vainqueurs.appariement_manuel_officiel is True

    # Deux vainqueurs de barrages distincts peuvent être associés directement
    # par tirage officiel, sans modifier ni relier leurs matchs sources.
    for club_id in (aster.id, nebula.id):
        await verifier_equipe_directement_nommable(
            db_fictif,
            saison.id,
            club_id,
            "quart",
            appariement_manuel_officiel=appariement_deux_vainqueurs.appariement_manuel_officiel,
        )

    # Un qualifié direct d'une autre voie peut aussi être apparié à un vainqueur.
    appariement_mixte = MatchCreate(
        saison_id=saison.id,
        date_heure=datetime(2042, 6, 3, tzinfo=timezone.utc),
        phase="quart",
        equipe_domicile_id=aster.id,
        equipe_exterieur_id=direct.id,
        appariement_manuel_officiel=True,
    )
    assert appariement_mixte.appariement_manuel_officiel is True
    await verifier_equipe_directement_nommable(
        db_fictif,
        saison.id,
        direct.id,
        "quart",
        appariement_manuel_officiel=appariement_mixte.appariement_manuel_officiel,
    )

    for perdant_id in (lynx.id, comete.id):
        with pytest.raises(HTTPException) as loser_stays_blocked:
            await verifier_equipe_directement_nommable(
                db_fictif,
                saison.id,
                perdant_id,
                "quart",
                appariement_manuel_officiel=True,
            )
        assert loser_stays_blocked.value.status_code == 409
        assert "éliminée" in loser_stays_blocked.value.detail

    with pytest.raises(HTTPException) as pending_team_blocked:
        await verifier_equipe_directement_nommable(
            db_fictif,
            saison.id,
            non_confirme.id,
            "quart",
            appariement_manuel_officiel=True,
        )
    assert pending_team_blocked.value.status_code == 409
    assert "qualification validée" in pending_team_blocked.value.detail
