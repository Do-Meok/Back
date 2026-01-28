import pytest
from datetime import date, datetime
from domains.ingredient.models import Ingredient
from domains.ingredient.repository import IngredientRepository
from domains.refrigerator.models import Compartment, Refrigerator

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


@pytest.mark.asyncio
async def test_get_unassigned_ingredients_logic(db_session, test_user):
    """
    [Repository] 미분류 식재료 조회
    - 조건: compartment_id가 None인 식재료만 조회되어야 함
    - 검증: 특정 칸(Compartment)에 할당된 재료는 조회되지 않아야 함
    """
    repo = IngredientRepository(db_session)

    # 1. 테스트를 위한 기반 데이터 생성 (User -> Refrigerator -> Compartment)

    # [수정] 스키마에 맞춰 필수 필드(pos_x, pos_y) 포함 및 없는 필드(type) 제거
    fridge = Refrigerator(
        user_id=test_user.id,
        name="테스트냉장고",
        pos_x=1,  # NOT NULL constraints
        pos_y=1  # NOT NULL constraints
    )
    db_session.add(fridge)
    await db_session.commit()
    await db_session.refresh(fridge)

    # [수정] 스키마에 맞춰 필수 필드(order_index) 포함 및 없는 필드(type) 제거
    comp = Compartment(
        refrigerator_id=fridge.id,
        name="야채칸",
        order_index=1  # NOT NULL constraints
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    real_compartment_id = comp.id

    # 2. 식재료 데이터 준비

    # (A) 미분류 식재료 (우리가 조회하려는 대상 -> compartment_id IS NULL)
    unassigned_ing = Ingredient(
        user_id=test_user.id,
        ingredient_name="미분류양파",
        purchase_date=TODAY,
        compartment_id=None
    )

    # (B) 분류된 식재료 (조회되면 안 됨 -> compartment_id IS NOT NULL)
    assigned_ing = Ingredient(
        user_id=test_user.id,
        ingredient_name="칸에있는두부",
        purchase_date=TODAY,
        compartment_id=real_compartment_id
    )

    # (C) 삭제된 식재료 (조회되면 안 됨)
    deleted_ing = Ingredient(
        user_id=test_user.id,
        ingredient_name="삭제된고기",
        purchase_date=TODAY,
        compartment_id=None,
        deleted_at=datetime.now()
    )

    await repo.add_ingredients([unassigned_ing, assigned_ing, deleted_ing])

    # When: 미분류 식재료 조회 실행
    results = await repo.get_unassigned_ingredients(test_user.id)

    # Then
    assert len(results) == 1
    assert results[0].ingredient_name == "미분류양파"
    assert results[0].compartment_id is None

    @pytest.mark.asyncio
    async def test_bulk_update_compartment(db_session, test_user):
        """[Repository] 다중 식재료 compartment_id 일괄 업데이트"""
        repo = IngredientRepository(db_session)

        # Given: 미분류 식재료 3개 생성
        ing1 = Ingredient(user_id=test_user.id, ingredient_name="재료1", purchase_date=TODAY, compartment_id=None)
        ing2 = Ingredient(user_id=test_user.id, ingredient_name="재료2", purchase_date=TODAY, compartment_id=None)
        ing3 = Ingredient(user_id=test_user.id, ingredient_name="재료3", purchase_date=TODAY, compartment_id=None)

        await repo.add_ingredients([ing1, ing2, ing3])

        target_ids = [ing1.id, ing2.id]  # 3번은 제외하고 1, 2번만 이동
        target_compartment_id = 5

        # When: 일괄 업데이트 실행
        count = await repo.bulk_update_compartment(target_ids, target_compartment_id, test_user.id)

        # Then
        assert count == 2  # 2개가 업데이트되어야 함

        # DB 상태 확인
        await db_session.refresh(ing1)
        await db_session.refresh(ing3)

        assert ing1.compartment_id == 5  # 변경됨
        assert ing3.compartment_id is None  # 변경 안 됨