from datetime import datetime, timedelta

import fakeredis.aioredis
import pytest

from core.exception.exceptions import RateLimitExceededException
from core.quota import KST, DailyQuotaStore


@pytest.fixture
async def redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


@pytest.fixture
def store(redis) -> DailyQuotaStore:
    return DailyQuotaStore(redis)


async def test_consume_allows_up_to_limit(store: DailyQuotaStore):
    for expected_remaining in (4, 3, 2, 1, 0):
        info = await store.consume("kind", "user-1", 5)
        assert info.remaining == expected_remaining
        assert info.limit == 5


async def test_consume_raises_when_limit_exceeded(store: DailyQuotaStore):
    for _ in range(5):
        await store.consume("kind", "user-1", 5)

    with pytest.raises(RateLimitExceededException):
        await store.consume("kind", "user-1", 5)


async def test_consume_is_scoped_per_kind_and_identifier(store: DailyQuotaStore):
    for _ in range(5):
        await store.consume("kind-a", "user-1", 5)

    # 다른 kind, 다른 identifier는 서로 영향을 주지 않음
    info_other_kind = await store.consume("kind-b", "user-1", 5)
    info_other_user = await store.consume("kind-a", "user-2", 5)
    assert info_other_kind.remaining == 4
    assert info_other_user.remaining == 4


async def test_get_remaining_does_not_consume(store: DailyQuotaStore):
    before = await store.get_remaining("kind", "user-1", 5)
    assert before.used == 0
    assert before.remaining == 5

    await store.consume("kind", "user-1", 5)

    after = await store.get_remaining("kind", "user-1", 5)
    assert after.used == 1
    assert after.remaining == 4

    # get_remaining 자체는 소모하지 않으므로 반복 호출해도 값이 그대로여야 함
    again = await store.get_remaining("kind", "user-1", 5)
    assert again.used == 1


async def test_quota_resets_on_a_different_kst_day(store: DailyQuotaStore, monkeypatch: pytest.MonkeyPatch):
    for _ in range(5):
        await store.consume("kind", "user-1", 5)
    with pytest.raises(RateLimitExceededException):
        await store.consume("kind", "user-1", 5)

    tomorrow = datetime.now(KST) + timedelta(days=1)

    import core.quota as quota_module

    monkeypatch.setattr(quota_module, "_kst_today", lambda: tomorrow.date())

    # 날짜(키)가 바뀌었으니 다시 처음부터 5회 소모 가능해야 함
    info = await store.consume("kind", "user-1", 5)
    assert info.remaining == 4
