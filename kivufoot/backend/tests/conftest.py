"""
Fixtures pytest partagées.

IMPORTANT : ces tests nécessitent un vrai PostgreSQL (colonnes JSONB et
contraintes CHECK spécifiques à PostgreSQL utilisées dans les
migrations). Utilisez le service `db_test` du docker-compose fourni -
voir README.md, section "Lancer les tests".

Isolation : chaque test tourne dans une transaction externe qui englobe
une SAVEPOINT ; même si le code testé appelle session.commit(), seul le
savepoint est validé - la transaction externe est annulée (rollback) à
la fin du test, donc aucun test ne pollue les suivants ni les données
DEMO. C'est le pattern documenté par SQLAlchemy pour les suites de
tests ("Joining a Session into an External Transaction").
"""
import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://kivufoot:kivufoot@localhost:5433/kivufoot_test"
)

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    async with engine.connect() as connection:
        outer_transaction = await connection.begin()
        session_factory = async_sessionmaker(bind=connection, expire_on_commit=False, autoflush=False)
        session: AsyncSession = session_factory()

        nested = await connection.begin_nested()

        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sync_session, transaction):
            nonlocal nested
            if not nested.is_active:
                nested = connection.sync_connection.begin_nested()

        try:
            yield session
        finally:
            await session.close()
            if outer_transaction.is_active:
                await outer_transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
