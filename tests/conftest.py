import os
from collections.abc import AsyncGenerator
from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("PHONE_AES_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("HMAC_SECRET", "test-hmac-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("NAVER_OCR_SECRET_KEY", "test-naver-ocr-secret")
os.environ.setdefault("NAVER_OCR_API_URL", "https://example.com/ocr")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_USER", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("SMTP_FROM_EMAIL", "test@test.com")
os.environ.setdefault("KAKAO_REST_API_KEY", "test-kakao-key")
os.environ.setdefault("KAKAO_CLIENT_SECRET", "test-kakao-client-secret")
os.environ.setdefault("KAKAO_REDIRECT_URI", "https://example.com/redirect")

import fakeredis.aioredis

from api.deps import get_email_service
from core import redis as redis_module
from core import security
from core.database import Base, get_db
from domains.auth.email_service import EmailService
from domains.ingredient.model import Ingredient
from domains.saved_recipe.model import SavedRecipe  # noqa: F401
from domains.user.model import User
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class CapturingEmailService(EmailService):
    """실제 발송 대신 (email -> code)를 기억해서 테스트가 인증 코드를 읽을 수 있게 함"""

    def __init__(self) -> None:
        super().__init__(backend="console")
        self.sent_codes: dict[str, str] = {}

    async def send_verification_code(self, to_email: str, code: str, purpose: str) -> None:
        self.sent_codes[to_email] = code


@pytest_asyncio.fixture
async def db_engine():
    # SQLite는 BIGINT autoincrement를 지원하지 않아 테스트용으로 Integer로 교체
    Ingredient.__table__.c.id.type = Integer()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
def email_service_stub() -> CapturingEmailService:
    return CapturingEmailService()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, email_service_stub: CapturingEmailService) -> AsyncGenerator[AsyncClient]:
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_module._redis = fake

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: email_service_stub
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        await fake.aclose()
        redis_module._redis = None


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        password=security.hash_password("password123"),
        nickname="testuser",
        name="테스트유저",
        birth=date(1990, 1, 1),
        phone=security.encrypt_phone("010-0000-0000"),
        phone_hash=security.make_phone_hash("010-0000-0000"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    token = security.create_jwt(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_ingredient(db_session: AsyncSession, test_user: User) -> Ingredient:
    ingredient = Ingredient(
        user_id=test_user.id,
        ingredient_name="양파",
    )
    db_session.add(ingredient)
    await db_session.flush()
    return ingredient
