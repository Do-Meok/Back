import fakeredis.aioredis
import pytest

from core.exception.exceptions import ConflictException
from domains.auth.signup_pending_store import PendingSignup, SignupPendingStore


@pytest.fixture
async def redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


@pytest.fixture
def store(redis) -> SignupPendingStore:
    return SignupPendingStore(redis)


def _pending(email: str = "test@example.com", nickname: str = "testuser") -> PendingSignup:
    return PendingSignup(
        email=email,
        password_hash="hashed",
        nickname=nickname,
        name="테스트",
        birth="1990-01-01",
        phone="encrypted-phone",
        phone_hash="phone-hash",
    )


async def test_upsert_then_get_roundtrip(store: SignupPendingStore):
    await store.upsert(_pending())

    result = await store.get("test@example.com")

    assert result is not None
    assert result.nickname == "testuser"


async def test_get_returns_none_when_missing(store: SignupPendingStore):
    assert await store.get("missing@example.com") is None


async def test_upsert_rejects_nickname_used_by_different_email(store: SignupPendingStore):
    await store.upsert(_pending(email="a@example.com", nickname="dupnick"))

    with pytest.raises(ConflictException):
        await store.upsert(_pending(email="b@example.com", nickname="dupnick"))


async def test_upsert_allows_reusing_own_nickname(store: SignupPendingStore):
    await store.upsert(_pending(email="a@example.com", nickname="mynick"))

    # 동일 이메일이 같은 닉네임으로 다시 upsert 해도 충돌이 아니어야 함
    await store.upsert(_pending(email="a@example.com", nickname="mynick"))

    result = await store.get("a@example.com")
    assert result is not None
    assert result.nickname == "mynick"


async def test_upsert_releases_previous_nickname_when_changed(store: SignupPendingStore):
    await store.upsert(_pending(email="a@example.com", nickname="oldnick"))
    await store.upsert(_pending(email="a@example.com", nickname="newnick"))

    # 이전 닉네임은 해제되어 다른 이메일이 사용할 수 있어야 함
    await store.upsert(_pending(email="b@example.com", nickname="oldnick"))

    result = await store.get("b@example.com")
    assert result is not None
    assert result.nickname == "oldnick"


async def test_pop_removes_entry_and_returns_it(store: SignupPendingStore):
    await store.upsert(_pending())

    popped = await store.pop("test@example.com")

    assert popped is not None
    assert popped.email == "test@example.com"
    assert await store.get("test@example.com") is None


async def test_pop_returns_none_when_missing(store: SignupPendingStore):
    assert await store.pop("missing@example.com") is None
