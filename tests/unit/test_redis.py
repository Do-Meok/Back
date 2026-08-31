from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import RedisError

import core.redis as redis_module


@pytest.fixture(autouse=True)
def reset_redis_module():
    redis_module._redis = None
    yield
    redis_module._redis = None


def test_get_redis_raises_when_not_initialized():
    with pytest.raises(RuntimeError):
        redis_module.get_redis()


async def test_init_redis_sets_client_and_pings(monkeypatch: pytest.MonkeyPatch):
    fake_client = AsyncMock()
    from_url = MagicMock(return_value=fake_client)
    monkeypatch.setattr(redis_module, "Redis", MagicMock(from_url=from_url))

    await redis_module.init_redis()

    from_url.assert_called_once()
    fake_client.ping.assert_awaited_once()
    assert redis_module.get_redis() is fake_client


async def test_init_redis_survives_ping_failure(monkeypatch: pytest.MonkeyPatch):
    fake_client = AsyncMock()
    fake_client.ping.side_effect = RedisError("연결 실패")
    monkeypatch.setattr(redis_module, "Redis", MagicMock(from_url=MagicMock(return_value=fake_client)))

    await redis_module.init_redis()

    # 핑에 실패해도 서버는 계속 떠 있어야 하므로 클라이언트는 그대로 설정되어 있어야 함
    assert redis_module.get_redis() is fake_client


async def test_init_redis_raises_when_client_creation_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        redis_module,
        "Redis",
        MagicMock(from_url=MagicMock(side_effect=ValueError("잘못된 URL"))),
    )

    with pytest.raises(ValueError):
        await redis_module.init_redis()


async def test_close_redis_clears_client():
    fake_client = AsyncMock()
    redis_module._redis = fake_client

    await redis_module.close_redis()

    fake_client.aclose.assert_awaited_once()
    with pytest.raises(RuntimeError):
        redis_module.get_redis()


async def test_close_redis_is_noop_when_not_initialized():
    redis_module._redis = None

    await redis_module.close_redis()  # 예외 없이 통과해야 함
