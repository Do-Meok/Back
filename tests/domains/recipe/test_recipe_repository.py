import pytest
from domains.recipe.repository import RecipeRepository


@pytest.mark.asyncio
async def test_save_recipe_success(db_session, test_user):
    """[Repository] 레시피 저장 테스트 (JSONB)"""
    repo = RecipeRepository(db_session)

    # Given
    recipe_data = {
        "food": "김치찌개",
        "use_ingredients": [{"name": "김치", "amount": "1포기"}],
        "steps": ["끓인다"],
        "tip": "맛있다",
        "difficulty": 3,
    }

    # When
    saved_entity = await repo.save_recipe(
        user_id=test_user.id, food_name="김치찌개", recipe=recipe_data
    )

    # Then
    assert saved_entity.id is not None
    assert saved_entity.recipe["food"] == "김치찌개"
    assert saved_entity.recipe["difficulty"] == 3


@pytest.mark.asyncio
async def test_get_recipes_ordering(db_session, test_user):
    """[Repository] 레시피 목록 조회 (최신순 정렬 확인)"""
    repo = RecipeRepository(db_session)

    # Given: 2개의 레시피 저장
    await repo.save_recipe(test_user.id, "라면", {"food": "라면", "steps": []})
    await repo.save_recipe(
        test_user.id, "볶음밥", {"food": "볶음밥", "steps": []}
    )  # 이게 더 나중에 생성됨

    # When
    results = await repo.get_recipes(test_user.id)

    # Then
    assert len(results) == 2
    assert results[0].food_name == "볶음밥"  # 나중에 만든 게 먼저 나와야 함 (DESC)
    assert results[1].food_name == "라면"
