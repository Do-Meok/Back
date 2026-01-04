import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from core.database import get_postgres_db, Base

# 테스트용 인메모리 SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    세션(테스트 전체) 범위의 엔진 생성
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield engine

    # 테스트 세션이 끝나면 엔진 종료 -> 무한 테스트 막기
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):

    # 테이블 생성
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 세션 팩토리 생성 (엔진과 바인딩)
    session_factory = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # 세션 연결 및 반환
    async with session_factory() as session:
        yield session

    # 테이블 삭제 (테스트 간 데이터 격리)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_postgres_db():
        yield db_session

    app.dependency_overrides[get_postgres_db] = override_get_postgres_db

    async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()