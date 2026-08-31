from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
import uuid6
from langchain_core.documents import Document

from core.exception.exceptions import RateLimitExceededException
from core.quota import QuotaInfo
from domains.rag.service import RagService
from domains.user.model import User


@pytest.fixture
def ingredient_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def retriever() -> MagicMock:
    return MagicMock()


@pytest.fixture
def daily_quota_store() -> AsyncMock:
    store = AsyncMock()
    store.consume.return_value = QuotaInfo(limit=5, used=1, remaining=4)
    store.get_remaining.return_value = QuotaInfo(limit=5, used=0, remaining=5)
    return store


@pytest.fixture
def user() -> User:
    return User(
        id=uuid6.uuid7(),
        email="test@example.com",
        nickname="testuser",
        name="테스트유저",
        birth=date(1990, 1, 1),
    )


@pytest.fixture
def rag_service(
    user: User, ingredient_repo: AsyncMock, retriever: MagicMock, daily_quota_store: AsyncMock
) -> RagService:
    return RagService(
        user=user,
        ingredient_repo=ingredient_repo,
        retriever=retriever,
        daily_quota_store=daily_quota_store,
    )


async def test_recommend_recipes_without_ingredients_does_not_consume_quota(
    rag_service: RagService, ingredient_repo: AsyncMock, daily_quota_store: AsyncMock, retriever: MagicMock
):
    ingredient_repo.get_ingredients.return_value = []

    response = await rag_service.recommend_recipes()

    assert response.recipes == []
    assert response.quota_remaining == 5
    daily_quota_store.consume.assert_not_awaited()
    daily_quota_store.get_remaining.assert_awaited_once()
    retriever.search.assert_not_called()


async def test_recommend_recipes_consumes_quota_and_returns_remaining(
    rag_service: RagService, ingredient_repo: AsyncMock, daily_quota_store: AsyncMock, retriever: MagicMock, user: User
):
    ingredient_repo.get_ingredients.return_value = [MagicMock(ingredient_name="양파")]
    retriever.search.return_value = [
        (
            Document(
                page_content="parsed_ingredients: 양파, 감자",
                metadata={"recipe_name": "감자볶음"},
            ),
            0.1,
        )
    ]

    response = await rag_service.recommend_recipes()

    assert response.quota_remaining == 4
    daily_quota_store.consume.assert_awaited_once_with("rag_search", str(user.id), 5)


async def test_recommend_recipes_blocked_when_quota_exceeded(
    rag_service: RagService, ingredient_repo: AsyncMock, daily_quota_store: AsyncMock, retriever: MagicMock
):
    ingredient_repo.get_ingredients.return_value = [MagicMock(ingredient_name="양파")]
    daily_quota_store.consume.side_effect = RateLimitExceededException()

    with pytest.raises(RateLimitExceededException):
        await rag_service.recommend_recipes()

    retriever.search.assert_not_called()
