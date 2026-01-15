import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport

from main import app
from core.database import get_db, Base
from core.di import get_current_user

from domains.user.models import User


@pytest.fixture(scope="session")
def postgres_container():
    postgres = PostgresContainer("postgres:15-alpine")
    postgres.start()
    yield postgres
    postgres.stop()


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_container):
    connection_url = postgres_container.get_connection_url().replace(
        "psycopg2", "asyncpg"
    )
    engine = create_async_engine(connection_url, echo=False, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def init_db(db_engine):
    async with db_engine.connect() as conn:
        await conn.execute(
            text("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid <> pg_backend_pid()
            AND datname = current_database();
        """)
        )

        tables = list(Base.metadata.tables.keys())
        if tables:
            await conn.execute(
                text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;")
            )
            await conn.commit()
    yield


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session
        await session.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    async def override_get_postgres_db():
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_postgres_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        nickname="테스트유저",
        password="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def authorized_client(client, test_user):
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield client
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
