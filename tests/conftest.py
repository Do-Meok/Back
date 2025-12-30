import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

# 사용자의 파일 구조에 맞춰 import
from src.main import app
from src.core.connection import get_postgres_db

# ❌ Base import 제거함 (아직 ORM 미구현)

# 1. 테스트용 DB URL (SQLite In-Memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    # 2. 비동기 엔진 생성
    # In-Memory SQLite는 스레드 간 연결 공유를 위해 StaticPool 필수
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # ❌ ORM이 없으므로 테이블 생성(create_all) 로직 제거
    # 현재는 빈 깡통 DB 엔진만 생성됩니다.

    yield engine

    # ❌ 테이블 삭제(drop_all) 로직 제거
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    # 3. 테스트용 비동기 세션 팩토리 생성
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )

    async with session_factory() as session:
        yield session
        # 테스트 내 변경사항 롤백
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    # 4. FastAPI 의존성 오버라이드
    # 실제 get_postgres_db 대신 테스트용 세션을 주입
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_postgres_db] = _get_test_db

    # 5. 비동기 HTTP Client 생성
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # 테스트 종료 후 오버라이드 해제
    app.dependency_overrides.clear()