import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport

from main import app
from core.database import get_db, Base, get_redis  # [중요] get_redis 임포트
from core.di import get_current_user
from domains.user.models import User


# --- 1. Postgres (RDBMS는 실제 동작 검증을 위해 컨테이너 유지 추천) ---
@pytest.fixture(scope="session")
def postgres_container():
    """Postgres 컨테이너는 계속 사용 (SQL 검증용)"""
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
    """매 테스트마다 DB 데이터 초기화"""
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


# --- 2. [핵심] Redis를 가짜(Mock)로 만들기 ---
@pytest.fixture(scope="function")
def mock_redis():
    """진짜 Redis 대신 사용할 가짜 객체"""
    mock = AsyncMock()

    # 기본 동작 설정 (테스트가 안 터지게만 설정)
    mock.set.return_value = True
    mock.delete.return_value = 1  # 1개 삭제됨 (성공)

    # get 호출 시 반환할 기본값 (필요하면 테스트 함수 안에서 재정의 가능)
    # 기본적으로는 "저장된 유저가 있다"고 가정
    mock.get.return_value = "user-uuid-123"

    return mock


# --- 3. Client 설정 (Dependency Override 적용) ---
@pytest_asyncio.fixture(scope="function")
async def client(db_engine, mock_redis):  # 여기에 mock_redis 주입
    # (1) DB 의존성 교체
    async def override_get_db():
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            try:
                yield session
            finally:
                await session.close()

    # (2) [핵심] Redis 의존성 교체
    # 앱(API)이 get_redis()를 부르면 -> 우리가 만든 mock_redis를 줌
    async def override_get_redis():
        yield mock_redis

    # FastAPI 앱에 오버라이드 등록
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # 테스트 끝나면 오버라이드 해제
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
