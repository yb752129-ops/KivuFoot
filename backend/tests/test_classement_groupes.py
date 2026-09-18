import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.models.enums import StatutMatch
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.club import Club
from app.models.competition import Saison, SaisonClub
from app.models.match import Match
from app.services.calcul_classement import calculer_classement
from app.services.groupes_saison import determiner_groupe_match

GROUPES_SAISON_2 = {
    "A": ["G.C.V", "INFO-2026", "G.G.T-GRF", "SANTÉ PUBLIC"],
    "B": ["G.G.T-2025", "INFO-2024+2025", "EGA", "+243(SAE)"],
    "C": ["SIF", "NUTRITION + OPHTALMOLOGIE", "LES CHAMPIONS", "G.G.T-2026"],
    "D": ["DROIT", "FC ESPOIR", "ANR"],
}


async def seed_saison_2(db_session):
    clubs = []
    ids_par_nom = {}
    next_id = 1

    for groupe, noms in GROUPES_SAISON_2.items():
        for nom in noms:
            club = Club(id=next_id, nom=nom, ville="Bujumbura")
            clubs.append(club)
            ids_par_nom[nom] = next_id
            next_id += 1

    db_session.add_all(clubs)
    db_session.add(Saison(id=2, competition_id=1, nom="Saison 2"))
    db_session.add_all(
        SaisonClub(
            saison_id=2,
            club_id=ids_par_nom[nom],
            groupe=groupe,
        )
        for groupe, noms in GROUPES_SAISON_2.items()
        for nom in noms
    )
    await db_session.commit()
    return ids_par_nom


def match_kwargs(dom_id, ext_id, **extra):
    values = {
        "saison_id": 2,
        "date_heure": datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
        "equipe_domicile_id": dom_id,
        "equipe_exterieur_id": ext_id,
        "phase": "poule",
        "groupe": "A",
    }
    values.update(extra)
    return values






@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    tables = [Club.__table__, Saison.__table__, SaisonClub.__table__, Match.__table__]

    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync: Base.metadata.create_all(sync, tables=tables)
        )

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_toutes_les_inscriptions_apparaissent_sans_match_valide(db_session):
    ids = await seed_saison_2(db_session)

    lignes = await calculer_classement(db_session, 2)

    assert len(lignes) == 15
    anr = next(ligne for ligne in lignes if ligne.club_nom == "ANR")
    assert anr.club_id == ids["ANR"]
    assert anr.points == 0
    assert anr.matchs_joues == 0
    assert anr.victoires == anr.nuls == anr.defaites == 0
    assert anr.buts_marques == anr.buts_encaisses == anr.difference_buts == 0


@pytest.mark.asyncio
async def test_seuls_les_matchs_valides_comptent(db_session):
    ids = await seed_saison_2(db_session)
    statuts_ignores = (
        StatutMatch.TERMINE,
        StatutMatch.PROGRAMME,
        StatutMatch.EN_COURS,
        StatutMatch.CONTESTE,
    )
    for index, statut in enumerate(statuts_ignores):
        db_session.add(
            Match(
                **match_kwargs(
                    ids["G.C.V"],
                    ids["INFO-2026"],
                    score_domicile=5 + index,
                    score_exterieur=0,
                    statut=statut,
                )
            )
        )
    await db_session.commit()

    lignes = await calculer_classement(db_session, 2)

    assert all(ligne.points == 0 and ligne.matchs_joues == 0 for ligne in lignes)


@pytest.mark.asyncio
async def test_match_valide_met_a_jour_uniquement_les_deux_equipes(db_session):
    ids = await seed_saison_2(db_session)
    db_session.add(
        Match(
            **match_kwargs(
                ids["G.C.V"],
                ids["INFO-2026"],
                score_domicile=2,
                score_exterieur=1,
                statut=StatutMatch.VALIDE,
                # Le filtre doit lire SaisonClub.groupe, pas cette copie.
                groupe="D",
            )
        )
    )
    await db_session.commit()

    general = await calculer_classement(db_session, 2)
    par_nom = {ligne.club_nom: ligne for ligne in general}
    assert (par_nom["G.C.V"].points, par_nom["G.C.V"].matchs_joues) == (3, 1)
    assert (par_nom["INFO-2026"].points, par_nom["INFO-2026"].matchs_joues) == (0, 1)
    assert par_nom["ANR"].points == 0 and par_nom["ANR"].matchs_joues == 0

    groupe_a = await calculer_classement(db_session, 2, groupe="A")
    assert {ligne.club_nom for ligne in groupe_a} == {"G.C.V", "INFO-2026", "G.G.T-GRF", "SANTÉ PUBLIC"}
    assert next(ligne for ligne in groupe_a if ligne.club_nom == "G.C.V").points == 3

    groupe_d = await calculer_classement(db_session, 2, groupe="D")
    assert {ligne.club_nom for ligne in groupe_d} == {"DROIT", "FC ESPOIR", "ANR"}
    assert all(ligne.matchs_joues == 0 for ligne in groupe_d)


@pytest.mark.asyncio
async def test_filtres_a_b_c_d_utilisent_la_configuration_de_la_saison(db_session):
    await seed_saison_2(db_session)

    attendus = {
        "A": {"G.C.V", "INFO-2026", "G.G.T-GRF", "SANTÉ PUBLIC"},
        "B": {"G.G.T-2025", "INFO-2024+2025", "EGA", "+243(SAE)"},
        "C": {"SIF", "NUTRITION + OPHTALMOLOGIE", "LES CHAMPIONS", "G.G.T-2026"},
        "D": {"DROIT", "FC ESPOIR", "ANR"},
    }

    for groupe, noms in attendus.items():
        lignes = await calculer_classement(db_session, 2, groupe=groupe)
        assert {ligne.club_nom for ligne in lignes} == noms
        assert all(ligne.matchs_joues == 0 for ligne in lignes)


@pytest.mark.asyncio
async def test_forfait_valide_compte_comme_trois_a_zero(db_session):
    ids = await seed_saison_2(db_session)
    db_session.add(
        Match(
            **match_kwargs(
                ids["DROIT"],
                ids["ANR"],
                score_domicile=3,
                score_exterieur=0,
                forfait=True,
                forfait_equipe="exterieur",
                statut=StatutMatch.VALIDE,
                groupe="D",
            )
        )
    )
    await db_session.commit()

    lignes = await calculer_classement(db_session, 2, groupe="D")
    par_nom = {ligne.club_nom: ligne for ligne in lignes}
    assert par_nom["DROIT"].points == 3
    assert par_nom["DROIT"].buts_marques == 3
    assert par_nom["ANR"].points == 0
    assert par_nom["ANR"].buts_encaisses == 3


@pytest.mark.asyncio
async def test_match_de_poule_refuse_des_groupes_officiels_differents(db_session):
    ids = await seed_saison_2(db_session)

    with pytest.raises(HTTPException) as erreur:
        await determiner_groupe_match(
            db_session,
            2,
            ids["G.C.V"],
            ids["G.G.T-2025"],
            "poule",
            "A",
        )
    assert erreur.value.status_code == 400
    assert "même groupe" in str(erreur.value.detail)

    assert (
        await determiner_groupe_match(
            db_session,
            2,
            ids["G.C.V"],
            ids["INFO-2026"],
            "poule",
            None,
        )
        == "A"
    )

    with pytest.raises(HTTPException) as contradiction:
        await determiner_groupe_match(
            db_session,
            2,
            ids["G.C.V"],
            ids["INFO-2026"],
            "poule",
            "B",
        )
    assert contradiction.value.status_code == 400
    assert "doit être A" in str(contradiction.value.detail)
