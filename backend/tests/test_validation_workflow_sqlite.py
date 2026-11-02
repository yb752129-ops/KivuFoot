import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.audit import AuditLog
from app.models.club import Club
from app.models.competition import Competition, Saison
from app.models.enums import (
    EquipeConcernee,
    PosteJoueur,
    RoleUtilisateur,
    StatutMatch,
    StatutParticipation,
    TypeCompetition,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.possession import PossessionMatch
from app.models.sport_engine import MatchQualificationSlot
from app.models.stats import StatistiqueJoueur
from app.models.user import User
from app.services.validation import valider_evenement, valider_match
from tests.sqlite_compat import utiliser_types_sqlite


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    tables = [
        Competition.__table__,
        Saison.__table__,
        Club.__table__,
        User.__table__,
        Joueur.__table__,
        Match.__table__,
        MatchParticipation.__table__,
        EvenementMatch.__table__,
        StatistiqueJoueur.__table__,
        MatchQualificationSlot.__table__,
        AuditLog.__table__,
        PossessionMatch.__table__,
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


@pytest.mark.asyncio
async def test_creation_joueur_feuille_evenements_et_validation_match(db_session):
    competition = Competition(
        nom="Compétition de test isolée",
        type=TypeCompetition.CHAMPIONNAT,
        est_demo=True,
    )
    db_session.add(competition)
    await db_session.flush()

    saison = Saison(competition_id=competition.id, nom="Saison de test")
    club_domicile = Club(nom="Équipe domicile", ville="Bujumbura")
    club_exterieur = Club(nom="Équipe extérieure", ville="Bujumbura")
    organisateur = User(
        email="workflow.organisateur@example.invalid",
        mot_de_passe_hash="test-only-not-a-real-hash",
        role=RoleUtilisateur.ADMIN,
        nom_complet="Compte de test isolé",
    )
    db_session.add_all([saison, club_domicile, club_exterieur, organisateur])
    await db_session.flush()

    joueur = Joueur(
        nom_complet="Nouveau joueur de test",
        poste=PosteJoueur.ATTAQUANT,
        club_actuel_id=club_domicile.id,
    )
    match = Match(
        saison_id=saison.id,
        date_heure=datetime.now(timezone.utc),
        equipe_domicile_id=club_domicile.id,
        equipe_exterieur_id=club_exterieur.id,
        phase="poule",
        statut=StatutMatch.EN_COURS,
        periode="2",
    )
    db_session.add_all([joueur, match])
    await db_session.flush()

    participation = MatchParticipation(
        match_id=match.id,
        joueur_id=joueur.id,
        club_id=club_domicile.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
        statut=StatutParticipation.TITULAIRE,
        numero=9,
    )
    but = EvenementMatch(
        match_id=match.id,
        minute=32,
        type=TypeEvenement.BUT,
        joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
        temp_id=uuid.uuid4(),
    )
    carton = EvenementMatch(
        match_id=match.id,
        minute=55,
        type=TypeEvenement.CARTON_JAUNE,
        joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE,
        temp_id=uuid.uuid4(),
    )
    db_session.add_all([participation, but, carton])
    await db_session.flush()

    await valider_evenement(db_session, but.id, organisateur.id)
    await valider_evenement(db_session, carton.id, organisateur.id)
    match.statut = StatutMatch.TERMINE
    await db_session.flush()
    await valider_match(db_session, match.id, organisateur.id)
    await db_session.flush()

    stats = await db_session.scalar(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur.id,
            StatistiqueJoueur.competition_id == competition.id,
            StatistiqueJoueur.saison_id == saison.id,
        )
    )
    assert await db_session.get(Joueur, joueur.id) is not None
    assert await db_session.get(MatchParticipation, participation.id) is not None
    assert match.statut == StatutMatch.VALIDE
    assert match.locked is True
    assert match.score_domicile == 1
    assert stats is not None
    assert (stats.buts, stats.cartons_jaunes, stats.matchs_joues, stats.titularisations) == (1, 1, 1, 1)
