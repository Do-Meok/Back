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
    saved_entity = await repo.save_recipe(user_id=test_user.id, food_name="김치찌개", recipe=recipe_data)

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
    await repo.save_recipe(test_user.id, "볶음밥", {"food": "볶음밥", "steps": []})  # 이게 더 나중에 생성됨

    # When
    results = await repo.get_recipes(test_user.id)

    # Then
    assert len(results) == 2
    assert results[0].food_name == "볶음밥"  # 나중에 만든 게 먼저 나와야 함 (DESC)
    assert results[1].food_name == "라면"


@pytest.mark.asyncio
async def test_get_recipe_by_id_success(db_session, test_user):
    """[Repository] 단일 레시피 ID로 조회 성공 테스트"""
    repo = RecipeRepository(db_session)

    # Given: 테스트용 레시피 저장
    recipe_data = {
        "food": "계란말이",
        "use_ingredients": [],
        "steps": ["계란을 푼다", "부친다"],
        "tip": "",
        "difficulty": 1,
    }
    saved_recipe = await repo.save_recipe(user_id=test_user.id, food_name="계란말이", recipe=recipe_data)

    # When: 방금 저장한 레시피의 ID로 조회
    found_recipe = await repo.get_recipe_by_id(saved_recipe.id)

    # Then
    assert found_recipe is not None
    assert found_recipe.id == saved_recipe.id
    assert found_recipe.food_name == "계란말이"
    assert found_recipe.recipe["steps"][0] == "계란을 푼다"


@pytest.mark.asyncio
async def test_get_recipe_by_id_not_found(db_session):
    """[Repository] 존재하지 않는 레시피 ID 조회 시 None 반환 테스트"""
    repo = RecipeRepository(db_session)

    # Given: DB에 없을 만한 임의의 ID
    invalid_recipe_id = 999999

    # When
    found_recipe = await repo.get_recipe_by_id(invalid_recipe_id)

    # Then: SQLAlchemy의 scalar_one_or_none()은 결과가 없으면 None을 반환해야 함
    assert found_recipe is None


@pytest.mark.asyncio
async def test_delete_recipe_success(db_session, test_user):
    """[Repository] 레시피 삭제 성공 테스트"""
    repo = RecipeRepository(db_session)

    # Given: 삭제할 레시피 생성
    recipe_data = {"food": "삭제될 요리", "steps": []}
    saved_recipe = await repo.save_recipe(user_id=test_user.id, food_name="삭제될 요리", recipe=recipe_data)

    # DB에 잘 들어갔는지 1차 확인
    assert await repo.get_recipe_by_id(saved_recipe.id) is not None

    # When: 생성한 레시피 객체를 넘겨서 삭제
    await repo.delete_recipe(saved_recipe)

    # Then: 삭제 후 다시 조회했을 때 None이어야 함
    deleted_recipe = await repo.get_recipe_by_id(saved_recipe.id)
    assert deleted_recipe is None
