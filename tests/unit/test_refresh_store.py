import uuid

import fakeredis.aioredis
import pytest

from core.exception.exceptions import ExternalServiceException
from domains.auth.refresh_store import RefreshTokenStore


@pytest.fixture
async def redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


@pytest.fixture
def store(redis) -> RefreshTokenStore:
    return RefreshTokenStore(redis, ttl_seconds=60)


async def test_save_and_pop_user_id_roundtrip(store: RefreshTokenStore):
    user_id = uuid.uuid4()
    await store.save("raw-token", user_id)

    popped = await store.pop_user_id("raw-token")

    assert popped == user_id
    # 팝 이후에는 동일 토큰으로 다시 조회할 수 없어야 함
    assert await store.pop_user_id("raw-token") is None


async def test_pop_user_id_returns_none_for_unknown_token(store: RefreshTokenStore):
    assert await store.pop_user_id("unknown-token") is None


async def test_delete_removes_token(store: RefreshTokenStore):
    user_id = uuid.uuid4()
    await store.save("raw-token", user_id)

    await store.delete("raw-token")

    assert await store.pop_user_id("raw-token") is None


async def test_delete_is_noop_for_unknown_token(store: RefreshTokenStore):
    await store.delete("unknown-token")  # 예외 없이 통과해야 함


async def test_revoke_all_for_user_removes_every_saved_token(store: RefreshTokenStore, redis):
    user_id = uuid.uuid4()
    await store.save("token-a", user_id)
    await store.save("token-b", user_id)

    await store.revoke_all_for_user(user_id)

    assert await store.pop_user_id("token-a") is None
    assert await store.pop_user_id("token-b") is None
    assert await redis.exists(store._user_set_key(user_id)) == 0


async def test_revoke_all_for_user_is_noop_when_no_tokens(store: RefreshTokenStore):
    await store.revoke_all_for_user(uuid.uuid4())  # 예외 없이 통과해야 함


async def test_save_raises_external_service_exception_on_redis_error(
    store: RefreshTokenStore, monkeypatch: pytest.MonkeyPatch
):
    def boom(*args, **kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(store._redis, "pipeline", boom)

    with pytest.raises(ExternalServiceException):
        await store.save("raw-token", uuid.uuid4())
