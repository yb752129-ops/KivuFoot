from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.actualite import Actualite, ActualiteImage, ActualiteLike, HommeMatch
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.enums import CategorieActualite, RoleUtilisateur, StatutActualite, StatutMatch, TypeCompetition
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.photo import Photo
from app.models.staff import Staff
from app.models.user import User
from app.routes.actualites import (
    aimer_actualite,
    creer_actualite,
    detail_actualite_publique,
    designer_homme_du_match,
    lister_actualites_publiques,
    publier_actualite,
)
from app.schemas.actualite import ActualiteCreate, HommeMatchCreate, LikePayload

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db_session(monkeypatch):
    async def aucun_audit(*args, **kwargs):
        return None

    monkeypatch.setattr("app.routes.actualites.log_audit", aucun_audit)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    tables = [
        User.__table__, Club.__table__, Competition.__table__, Saison.__table__, SaisonClub.__table__,
        OrganisateurCompetition.__table__, Photo.__table__, Staff.__table__, Joueur.__table__,
        Match.__table__, MatchParticipation.__table__, Actualite.__table__, ActualiteImage.__table__,
        ActualiteLike.__table__, HommeMatch.__table__,
    ]
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def contexte(db_session):
    admin = User(id=1, email="admin.actualites@test", mot_de_passe_hash="x", role=RoleUtilisateur.ADMIN, nom_complet="Admin")
    orga = User(id=2, email="orga.actualites@test", mot_de_passe_hash="x", role=RoleUtilisateur.ORGANISATEUR, nom_complet="Orga")
    autre = User(id=3, email="autre.actualites@test", mot_de_passe_hash="x", role=RoleUtilisateur.ORGANISATEUR, nom_complet="Autre")
    comp = Competition(id=10, nom="Tournoi réel", type=TypeCompetition.TOURNOI, est_demo=False)
    saison = Saison(id=20, competition_id=10, nom="2e édition")
    home = Club(id=30, nom="Équipe A", ville="Bujumbura")
    away = Club(id=31, nom="Équipe B", ville="Bujumbura")
    player = Joueur(id=40, nom_complet="Joueur A", date_naissance=date(2000, 1, 1), club_actuel_id=30)
    match = Match(
        id=50, saison_id=20, journee="J1", date_heure=datetime(2026, 9, 20, 8, tzinfo=timezone.utc),
        stade="Hope stadium", equipe_domicile_id=30, equipe_exterieur_id=31,
        score_domicile=1, score_exterieur=0, statut=StatutMatch.VALIDE, locked=True,
    )
    db_session.add_all([admin, orga, autre, comp, saison, home, away, player, match, OrganisateurCompetition(user_id=2, competition_id=10)])
    db_session.add_all([SaisonClub(saison_id=20, club_id=30), SaisonClub(saison_id=20, club_id=31)])
    await db_session.flush()
    return admin, orga, autre, match


async def test_brouillon_publicement_invisible_puis_publication_et_like(db_session):
    admin, _, _, match = await contexte(db_session)
    article = await creer_actualite(
        ActualiteCreate(
            titre="Retour sur la première journée",
            categorie=CategorieActualite.RETOUR_JOURNEE,
            texte="La première journée a été disputée dans un bon esprit sportif.",
            competition_id=10,
            saison_id=20,
            journee="J1",
            match_id=match.id,
        ),
        db_session,
        admin,
    )
    assert article.statut == StatutActualite.BROUILLON
    with pytest.raises(HTTPException) as invisible:
        await detail_actualite_publique(article.id, None, db_session)
    assert invisible.value.status_code == 404

    public = await publier_actualite(article.id, db_session, admin)
    assert public.statut == StatutActualite.PUBLIE
    listed = await lister_actualites_publiques(None, 10, 20, 0, db_session)
    assert [item.id for item in listed] == [article.id]

    liked = await aimer_actualite(article.id, LikePayload(client_token="client-token-000001"), db_session)
    assert liked.liked is True and liked.like_count == 1
    unliked = await aimer_actualite(article.id, LikePayload(client_token="client-token-000001"), db_session)
    assert unliked.liked is False and unliked.like_count == 0


async def test_actualite_mise_en_avant_prioritaire_dans_le_flux(db_session):
    admin, _, _, match = await contexte(db_session)
    normale = await creer_actualite(
        ActualiteCreate(
            titre="Information normale",
            categorie=CategorieActualite.ANNONCE,
            texte="Une information éditoriale normale est conservée.",
            competition_id=10,
            saison_id=20,
            match_id=match.id,
        ),
        db_session,
        admin,
    )
    une = await creer_actualite(
        ActualiteCreate(
            titre="Information importante",
            categorie=CategorieActualite.INFORMATION_IMPORTANTE,
            texte="Une information importante est mise en avant.",
            competition_id=10,
            saison_id=20,
            match_id=match.id,
            mise_en_avant=True,
        ),
        db_session,
        admin,
    )
    await publier_actualite(normale.id, db_session, admin)
    await publier_actualite(une.id, db_session, admin)
    listed = await lister_actualites_publiques(None, 10, 20, 0, db_session)
    assert listed[0].id == une.id
    assert listed[0].mise_en_avant is True
    assert normale.id in [item.id for item in listed]


async def test_organisateur_limite_a_sa_competition(db_session):
    _, orga, autre, match = await contexte(db_session)
    with pytest.raises(HTTPException) as erreur:
        await creer_actualite(
            ActualiteCreate(
                titre="Annonce hors périmètre",
                categorie=CategorieActualite.ANNONCE,
                texte="Cette annonce ne doit pas être créée par cet organisateur.",
                competition_id=10,
                match_id=match.id,
            ),
            db_session,
            autre,
        )
    assert erreur.value.status_code == 403
    article = await creer_actualite(
        ActualiteCreate(
            titre="Annonce autorisée",
            categorie=CategorieActualite.ANNONCE,
            texte="Annonce publiée dans la compétition autorisée.",
            competition_id=10,
            match_id=match.id,
        ),
        db_session,
        orga,
    )
    assert article.competition_id == 10


async def test_homme_du_match_designe_par_organisateur(db_session):
    _, orga, _, match = await contexte(db_session)
    homme = await designer_homme_du_match(match.id, HommeMatchCreate(joueur_id=40), db_session, orga)
    assert homme.joueur_id == 40
    assert homme.match_id == match.id


async def test_supporter_refuse_par_api_pour_creation_actualite(db_session):
    from app.auth.dependencies import get_current_user
    from app.database import get_db
    from app.main import app

    supporter = User(id=90, email="supporter.actualites@test", mot_de_passe_hash="x", role=RoleUtilisateur.SUPPORTER, nom_complet="Lecteur")
    db_session.add(supporter)
    await db_session.flush()

    async def override_db():
        yield db_session

    async def override_user():
        return supporter

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/actualites",
                json={"titre": "Tentative", "categorie": "annonce", "texte": "Publication interdite."},
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
