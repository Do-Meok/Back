import pytest
from datetime import date
from domains.ingredient.models import Ingredient
from domains.ingredient.repository import IngredientRepository

TODAY = date.today()


@pytest.mark.asyncio
async def test_add_and_get_ingredient(db_session, test_user):
    """[Repository] 식재료 저장 및 단일 조회"""
    repo = IngredientRepository(db_session)

    # Given
    ingredients = [
        Ingredient(
            user_id=test_user.id, ingredient_name="테스트양파", purchase_date=TODAY
        )
    ]

    # When
    saved_list = await repo.add_ingredients(ingredients)
    saved_id = saved_list[0].id

    # Then
    found = await repo.get_ingredient(saved_id, test_user.id)
    assert found is not None
    assert found.ingredient_name == "테스트양파"


@pytest.mark.asyncio
async def test_set_ingredient_details(db_session, test_user):
    """[Repository] 보관 정보(유통기한/장소) 설정"""
    repo = IngredientRepository(db_session)

    # 1. 저장
    ing = Ingredient(user_id=test_user.id, ingredient_name="우유", purchase_date=TODAY)
    saved = (await repo.add_ingredients([ing]))[0]

    # 2. 수정 (set_ingredient)
    exp_date = date(2099, 12, 31)
    updated = await repo.set_ingredient(
        saved.id, test_user.id, expiration_date=exp_date, storage_type="FRIDGE"
    )

    # 3. 검증
    assert updated.expiration_date == exp_date
    assert updated.storage_type == "FRIDGE"


@pytest.mark.asyncio
async def test_get_ingredients_filtering(db_session, test_user):
    """[Repository] 목록 조회 필터링 (미분류 vs 보관장소)"""
    repo = IngredientRepository(db_session)

    # Given:
    # 1) 미분류 (둘 다 없음) -> OK
    i1 = Ingredient(
        user_id=test_user.id, ingredient_name="미분류템", purchase_date=TODAY
    )

    # 2) 냉장 (✅ 수정: 보관장소가 있으면 유통기한도 있어야 함!)
    i2 = Ingredient(
        user_id=test_user.id,
        ingredient_name="냉장템",
        purchase_date=TODAY,
        storage_type="FRIDGE",
        expiration_date=TODAY,  # 👈 이걸 추가해주세요!
    )

    await repo.add_ingredients([i1, i2])

    # When A: 미분류 조회
    unclassified = await repo.get_ingredients(test_user.id, is_unclassified=True)

    # Then: 이제 정확히 1개만 나옵니다 (i1만)
    assert len(unclassified) == 1
    assert unclassified[0].ingredient_name == "미분류템"

    # When B: 냉장 조회
    fridge = await repo.get_ingredients(test_user.id, storage="FRIDGE")
    assert len(fridge) == 1
    assert fridge[0].ingredient_name == "냉장템"


@pytest.mark.asyncio
async def test_soft_delete(db_session, test_user):
    """[Repository] 삭제 시 deleted_at 갱신 및 조회 제외"""
    repo = IngredientRepository(db_session)

    ing = Ingredient(
        user_id=test_user.id, ingredient_name="삭제될거", purchase_date=TODAY
    )
    saved = (await repo.add_ingredients([ing]))[0]

    # When: 삭제
    success = await repo.delete_ingredient(saved.id, test_user.id)
    assert success is True

    # Then: 조회 안 돼야 함
    found = await repo.get_ingredient(saved.id, test_user.id)
    assert found is None
