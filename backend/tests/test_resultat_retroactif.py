from datetime import date, datetime, timezone

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
    StatutValidationEvenement,
    TypeCompetition,
)
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.stats import StatistiqueJoueur
from app.models.user import User
from app.routes.matchs import ajouter_buteurs_verifies, enregistrer_resultat_retroactif
from app.schemas.match import ButeurVerifieCreate, ButeursVerifiesCreate, MatchResultatRetroactif

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
    monkeypatch.setattr("app.services.validation.log_audit", aucun_audit)


async def contexte_match(db_session):
    competition = Competition(id=1, nom="Tournoi test", type=TypeCompetition.TOURNOI)
    saison = Saison(id=1, competition_id=1, nom="Saison test")
    domicile = Club(id=10, nom="G.G.T-2025", ville="Bukavu")
    exterieur = Club(id=11, nom="+243(SAE)", ville="Bukavu")
    inscription_dom = SaisonClub(saison_id=1, club_id=10, groupe="B")
    inscription_ext = SaisonClub(saison_id=1, club_id=11, groupe="B")
    match_ = Match(
        id=37,
        saison_id=1,
        date_heure=datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
        stade="Hope stadium",
        equipe_domicile_id=10,
        equipe_exterieur_id=11,
        groupe="B",
    )
    db_session.add_all([competition, saison, domicile, exterieur, inscription_dom, inscription_ext, match_])
    await db_session.flush()
    admin = User(id=1, email="admin@test.local", role=RoleUtilisateur.ADMIN, nom_complet="Admin test")
    return match_, domicile, exterieur, admin


async def test_resultat_retroactif_valide_et_verrouille_sans_evenement(db_session):
    match_, _, _, admin = await contexte_match(db_session)

    resultat = await enregistrer_resultat_retroactif(
        match_.id,
        MatchResultatRetroactif(
            score_domicile=1,
            score_exterieur=1,
            motif="Le match a été joué après confirmation administrative.",
            note_officielle="Résultat officiel 1–1. Les buteurs seront ajoutés après vérification.",
        ),
        db_session,
        admin,
    )

    assert resultat.score_domicile == 1
    assert resultat.score_exterieur == 1
    await db_session.refresh(match_)
    assert match_.statut == StatutMatch.VALIDE
    assert match_.locked is True
    assert match_.resultat_retroactif is True
    assert match_.buteurs_a_verifier is True
    events = (
        await db_session.execute(select(EvenementMatch).where(EvenementMatch.match_id == match_.id))
    ).scalars().all()
    assert events == []


async def test_buteurs_verifies_alimentent_stats_sans_doubler_score(db_session):
    match_, domicile, exterieur, admin = await contexte_match(db_session)
    buteur_dom = Joueur(
        id=101,
        nom_complet="Buteur domicile",
        date_naissance=date(2000, 1, 1),
        poste=PosteJoueur.ATTAQUANT,
        club_actuel_id=domicile.id,
    )
    buteur_ext = Joueur(
        id=102,
        nom_complet="Buteur extérieur",
        date_naissance=date(2000, 1, 1),
        poste=PosteJoueur.ATTAQUANT,
        club_actuel_id=exterieur.id,
    )
    db_session.add_all([buteur_dom, buteur_ext])
    await db_session.flush()

    await enregistrer_resultat_retroactif(
        match_.id,
        MatchResultatRetroactif(
            score_domicile=1,
            score_exterieur=1,
            motif="Rencontre jouée après rectification de la programmation.",
            note_officielle="Résultat officiel 1–1. Les buteurs seront ajoutés après vérification.",
        ),
        db_session,
        admin,
    )

    ajoutes = await ajouter_buteurs_verifies(
        match_.id,
        ButeursVerifiesCreate(
            buteurs=[
                ButeurVerifieCreate(joueur_id=buteur_dom.id, equipe_concernee=EquipeConcernee.DOMICILE),
                ButeurVerifieCreate(joueur_id=buteur_ext.id, equipe_concernee=EquipeConcernee.EXTERIEUR),
            ]
        ),
        db_session,
        admin,
    )

    assert len(ajoutes) == 2
    await db_session.refresh(match_)
    assert (match_.score_domicile, match_.score_exterieur) == (1, 1)
    assert match_.buteurs_a_verifier is False
    events = (
        await db_session.execute(select(EvenementMatch).where(EvenementMatch.match_id == match_.id))
    ).scalars().all()
    assert len(events) == 2
    assert all(e.statut_validation == StatutValidationEvenement.VALIDE for e in events)
    assert all(e.score_comptabilise is False for e in events)
    assert all(e.minute_connue is False for e in events)
    stats = (await db_session.execute(select(StatistiqueJoueur))).scalars().all()
    assert {stat.joueur_id: stat.buts for stat in stats} == {101: 1, 102: 1}
