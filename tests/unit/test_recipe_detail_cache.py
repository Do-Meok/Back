from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from redis.exceptions import RedisError

from domains.recipe_detail.cache import RecipeDetailCache, cache_key
from domains.recipe_detail.schemas import RecipeDetailResponse


def test_cache_key_normalizes_whitespace_and_case():
    assert cache_key("김치찌개", "홍길동") == cache_key("  김치찌개  ", "홍길동")
    assert cache_key("Kimchi", "Hong") == cache_key("kimchi", "hong")


def test_cache_key_differs_for_different_inputs():
    assert cache_key("김치찌개", "홍길동") != cache_key("된장찌개", "홍길동")


@pytest.fixture
async def redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


@pytest.fixture
def cache(redis) -> RecipeDetailCache:
    return RecipeDetailCache(redis, ttl_seconds=60)


def _detail() -> RecipeDetailResponse:
    return RecipeDetailResponse(
        board_name="김치찌개",
        author_name="홍길동",
        recipe_name="김치찌개",
        source_url="https://www.10000recipe.com/recipe/1",
        cached=False,
    )


async def test_get_returns_none_when_missing(cache: RecipeDetailCache):
    assert await cache.get("missing-key") is None


async def test_set_then_get_returns_cached_value(cache: RecipeDetailCache):
    key = cache_key("김치찌개", "홍길동")
    await cache.set(key, _detail())

    result = await cache.get(key)

    assert result is not None
    assert result.recipe_name == "김치찌개"
    assert result.cached is True


async def test_get_returns_none_on_redis_error(cache: RecipeDetailCache):
    cache._redis.get = AsyncMock(side_effect=RedisError("연결 실패"))

    assert await cache.get("any-key") is None


async def test_get_returns_none_on_corrupted_payload(cache: RecipeDetailCache):
    key = cache_key("김치찌개", "홍길동")
    await cache._redis.set(cache._redis_key(key), "not-json", ex=60)

    assert await cache.get(key) is None


async def test_set_stores_value_without_cached_flag(cache: RecipeDetailCache, redis):
    key = cache_key("김치찌개", "홍길동")
    await cache.set(key, _detail().model_copy(update={"cached": True}))

    raw = await redis.get(cache._redis_key(key))

    assert '"cached":false' in raw.replace(" ", "")
