from unittest.mock import AsyncMock

import pytest

from core.exception.exceptions import NotFoundException
from domains.recipe_detail.matcher import SearchCandidate
from domains.recipe_detail.schemas import RecipeDetailResponse
from domains.recipe_detail.service import RecipeDetailService


@pytest.fixture
def crawler() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def cache() -> AsyncMock:
    cache = AsyncMock()
    cache.get.return_value = None
    return cache


@pytest.fixture
def service(crawler: AsyncMock, cache: AsyncMock) -> RecipeDetailService:
    return RecipeDetailService(crawler=crawler, cache=cache)


def _raw_detail() -> RecipeDetailResponse:
    return RecipeDetailResponse(
        board_name="",
        author_name="",
        recipe_name="김치찌개",
        source_url="https://www.10000recipe.com/recipe/1",
        cached=False,
    )


async def test_get_detail_returns_cached_value_without_crawling(
    service: RecipeDetailService, crawler: AsyncMock, cache: AsyncMock
):
    cached = _raw_detail().model_copy(update={"cached": True})
    cache.get.return_value = cached

    result = await service.get_detail("김치찌개", "홍길동")

    assert result is cached
    crawler.search.assert_not_called()
    crawler.fetch_detail.assert_not_called()


async def test_get_detail_searches_and_caches_when_not_cached(
    service: RecipeDetailService, crawler: AsyncMock, cache: AsyncMock
):
    crawler.search.return_value = [SearchCandidate(recipe_id="1", title="김치찌개", author="홍길동")]
    crawler.fetch_detail.return_value = _raw_detail()

    result = await service.get_detail("김치찌개", "홍길동")

    crawler.search.assert_awaited_once_with("김치찌개")
    crawler.fetch_detail.assert_awaited_once_with("1")
    assert result.board_name == "김치찌개"
    assert result.author_name == "홍길동"
    assert result.cached is False
    cache.set.assert_awaited_once()


async def test_get_detail_strips_board_name_before_search(
    service: RecipeDetailService, crawler: AsyncMock, cache: AsyncMock
):
    crawler.search.return_value = [SearchCandidate(recipe_id="1", title="김치찌개", author="홍길동")]
    crawler.fetch_detail.return_value = _raw_detail()

    await service.get_detail("  김치찌개  ", "홍길동")

    crawler.search.assert_awaited_once_with("김치찌개")


async def test_get_detail_raises_not_found_when_no_candidate_matches(
    service: RecipeDetailService, crawler: AsyncMock, cache: AsyncMock
):
    crawler.search.return_value = [SearchCandidate(recipe_id="1", title="된장찌개", author="다른사람")]

    with pytest.raises(NotFoundException):
        await service.get_detail("김치찌개", "홍길동")

    crawler.fetch_detail.assert_not_called()
    cache.set.assert_not_called()
