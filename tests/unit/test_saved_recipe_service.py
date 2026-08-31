import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import uuid6

from core.exception.exceptions import BadRequestException, ConflictException, NotFoundException
from core.timezone import KST
from domains.recipe_detail.schemas import RecipeDetailResponse
from domains.saved_recipe.model import SavedRecipe
from domains.saved_recipe.schemas import SaveRecipeRequest
from domains.saved_recipe.service import SavedRecipeService, parse_mangae_source_id
from domains.user.model import User


def test_parse_mangae_source_id_splits_board_and_author():
    board, author = parse_mangae_source_id("김치찌개|홍길동")

    assert board == "김치찌개"
    assert author == "홍길동"


def test_parse_mangae_source_id_rejects_missing_separator():
    with pytest.raises(BadRequestException):
        parse_mangae_source_id("김치찌개")


def test_parse_mangae_source_id_rejects_empty_parts():
    with pytest.raises(BadRequestException):
        parse_mangae_source_id(" |홍길동")


@pytest.fixture
def user() -> User:
    return User(id=uuid6.uuid7(), email="test@example.com", nickname="testuser")


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def recipe_detail_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(user: User, repo: AsyncMock, recipe_detail_service: AsyncMock) -> SavedRecipeService:
    return SavedRecipeService(user=user, repo=repo, recipe_detail_service=recipe_detail_service)


def _detail() -> RecipeDetailResponse:
    return RecipeDetailResponse(
        board_name="김치찌개",
        author_name="홍길동",
        recipe_name="김치찌개",
        source_url="https://www.10000recipe.com/recipe/1",
        recipe_difficulty="아무나",
        time="30분",
    )


def _saved_recipe(**overrides) -> SavedRecipe:
    defaults = {
        "id": uuid6.uuid7(),
        "user_id": uuid6.uuid7(),
        "source": "mangae",
        "source_id": "김치찌개|홍길동",
        "recipe_name": "김치찌개",
        "recipe_difficulty": None,
        "time": None,
        "snapshot": {},
        "created_at": datetime.now(KST),
    }
    defaults.update(overrides)
    return SavedRecipe(**defaults)


async def test_save_raises_when_already_saved(service: SavedRecipeService, repo: AsyncMock, user: User):
    repo.find_by_source.return_value = _saved_recipe(user_id=user.id)

    with pytest.raises(ConflictException):
        await service.save(SaveRecipeRequest(source="mangae", source_id="김치찌개|홍길동"))


async def test_save_creates_snapshot_and_persists(
    service: SavedRecipeService, repo: AsyncMock, recipe_detail_service: AsyncMock, user: User
):
    repo.find_by_source.return_value = None
    recipe_detail_service.get_detail.return_value = _detail()
    saved = _saved_recipe(user_id=user.id, recipe_difficulty="아무나", time="30분")
    repo.add.return_value = saved

    result = await service.save(SaveRecipeRequest(source="mangae", source_id="김치찌개|홍길동"))

    recipe_detail_service.get_detail.assert_awaited_once_with("김치찌개", "홍길동")
    added_entity = repo.add.call_args.args[0]
    assert added_entity.recipe_name == "김치찌개"
    assert added_entity.snapshot["board_name"] == "김치찌개"
    assert result.id == saved.id


async def test_list_saved_returns_items(service: SavedRecipeService, repo: AsyncMock, user: User):
    repo.list_by_user.return_value = [_saved_recipe(user_id=user.id)]

    result = await service.list_saved()

    assert len(result) == 1
    repo.list_by_user.assert_awaited_once_with(user.id)


async def test_get_raises_when_not_found(service: SavedRecipeService, repo: AsyncMock):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await service.get(uuid.uuid4())


async def test_get_returns_detail(service: SavedRecipeService, repo: AsyncMock, user: User):
    entity = _saved_recipe(user_id=user.id)
    repo.get_by_id.return_value = entity

    result = await service.get(entity.id)

    assert result.id == entity.id


async def test_delete_raises_when_not_found(service: SavedRecipeService, repo: AsyncMock):
    repo.delete.return_value = False

    with pytest.raises(NotFoundException):
        await service.delete(uuid.uuid4())


async def test_delete_succeeds(service: SavedRecipeService, repo: AsyncMock, user: User):
    recipe_id = uuid6.uuid7()
    repo.delete.return_value = True

    await service.delete(recipe_id)

    repo.delete.assert_awaited_once_with(recipe_id, user.id)


async def test_status_rejects_non_mangae_source(service: SavedRecipeService):
    with pytest.raises(BadRequestException):
        await service.status("other", "a|b")


async def test_status_returns_saved_false_when_missing(service: SavedRecipeService, repo: AsyncMock):
    repo.find_by_source.return_value = None

    result = await service.status("mangae", "김치찌개|홍길동")

    assert result.saved is False
    assert result.id is None


async def test_status_returns_saved_true_when_found(service: SavedRecipeService, repo: AsyncMock, user: User):
    entity = _saved_recipe(user_id=user.id)
    repo.find_by_source.return_value = entity

    result = await service.status("mangae", "김치찌개|홍길동")

    assert result.saved is True
    assert result.id == entity.id
