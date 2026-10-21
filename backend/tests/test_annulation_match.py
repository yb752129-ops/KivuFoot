from datetime import date, datetime, timezone
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.club import Club
from app.models.competition import Competition, Saison, SaisonClub
from app.models.enums import (
    EquipeConcernee,
    PosteJoueur,
    RoleUtilisateur,
    StatutMatch,
    StatutParticipation,
    StatutValidationEvenement,
    TypeCompetition,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.stats import StatistiqueJoueur
from app.models.user import User
from app.routes.matchs import annuler_match, retablir_match
from app.schemas.match import MatchAnnulationCreate

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    tables = [
        Competition.__table__,
        Club.__table__,
        Saison.__table__,
        SaisonClub.__table__,
        Joueur.__table__,
        Match.__table__,
        MatchParticipation.__table__,
        EvenementMatch.__table__,
        StatistiqueJoueur.__table__,
    ]
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def desactiver_audit_sqlite(monkeypatch):
    async def aucun_audit(*args, **kwargs):
        return None

    monkeypatch.setattr("app.routes.matchs.log_audit", aucun_audit)


async def test_annulation_reversible_reconstruit_les_stats_sans_supprimer_les_faits(db_session):
    competition = Competition(id=1, nom="INFO-2026", type=TypeCompetition.TOURNOI)
    saison = Saison(id=1, competition_id=1, nom="INFO-2026")
    domicile = Club(id=10, nom="G.G.T", ville="Bujumbura")
    exterieur = Club(id=11, nom="GRF", ville="Bujumbura")
    joueur = Joueur(
        id=101,
        nom_complet="Buteur test",
        date_naissance=date(2000, 1, 1),
        poste=PosteJoueur.ATTAQUANT,
        club_actuel_id=10,
    )
    match_ = Match(
        id=37,
        saison_id=1,
        date_heure=datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc),
        equipe_domicile_id=10,
        equipe_exterieur_id=11,
        score_domicile=0,
        score_exterieur=3,
        statut=StatutMatch.VALIDE,
        locked=True,
    )
    participation = MatchParticipation(
        match_id=37,
        joueur_id=101,
        club_id=10,
        equipe_concernee=EquipeConcernee.DOMICILE,
        statut=StatutParticipation.TITULAIRE,
    )
    evenement = EvenementMatch(
        match_id=37,
        minute=12,
        type=TypeEvenement.BUT,
        joueur_id=101,
        equipe_concernee=EquipeConcernee.DOMICILE,
        statut_validation=StatutValidationEvenement.VALIDE,
        locked=True,
        refuse=False,
        temp_id=uuid.uuid4(),
    )
    admin = User(id=1, email="admin.annulation@test.example", role=RoleUtilisateur.ADMIN)
    db_session.add_all([
        competition,
        saison,
        domicile,
        exterieur,
        joueur,
        match_,
        participation,
        evenement,
        StatistiqueJoueur(
            joueur_id=101,
            competition_id=1,
            saison_id=1,
            matchs_joues=1,
            titularisations=1,
            buts=1,
            minutes_jouees=90,
        ),
    ])
    await db_session.flush()

    annule = await annuler_match(
        37,
        MatchAnnulationCreate(),
        db_session,
        admin,
    )

    assert annule.statut == StatutMatch.ANNULE
    assert annule.locked is True
    assert annule.annule_motif == "Décision de l'organisation"
    assert annule.statut_avant_annulation == StatutMatch.VALIDE.value
    assert annule.locked_avant_annulation is True
    assert await db_session.get(Match, 37) is not None
    assert await db_session.get(EvenementMatch, evenement.id) is not None
    assert (
        await db_session.execute(
            select(StatistiqueJoueur).where(StatistiqueJoueur.saison_id == 1)
        )
    ).scalars().all() == []

    retabli = await retablir_match(37, db_session, admin)

    assert retabli.statut == StatutMatch.VALIDE
    assert retabli.locked is True
    assert retabli.annule_motif is None
    restored_stats = (
        await db_session.execute(
            select(StatistiqueJoueur).where(
                StatistiqueJoueur.joueur_id == 101,
                StatistiqueJoueur.saison_id == 1,
            )
        )
    ).scalar_one()
    assert restored_stats.matchs_joues == 1
    assert restored_stats.titularisations == 1
    assert restored_stats.buts == 1
    assert restored_stats.minutes_jouees == 90
