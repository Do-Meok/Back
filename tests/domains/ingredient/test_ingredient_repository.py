import pytest
from datetime import date, timedelta
from sqlalchemy import select

from domains.ingredient.models import (
    Ingredient,
    IngredientExpiry,
    MissingIngredientLog,
    ExpiryDeviationLog,
)
from domains.ingredient.repository import IngredientRepository
from domains.refrigerator.models import Refrigerator, Compartment

TODAY = date.today()


@pytest.mark.asyncio
async def test_get_expiry_infos(db_session):
    """
    [New] 유통기한 메타 데이터(IngredientExpiry) 조회 테스트
    - 여러 개의 이름으로 조회 시, 존재하는 데이터만 Dict 형태로 반환되는지 확인
    """
    repo = IngredientRepository(db_session)

    # 1. 테스트 데이터 주입
    expiry_data_1 = IngredientExpiry(ingredient_name="양파", expiry_day=7, storage_type="ROOM")
    expiry_data_2 = IngredientExpiry(ingredient_name="우유", expiry_day=10, storage_type="FRIDGE")
    db_session.add_all([expiry_data_1, expiry_data_2])
    await db_session.commit()

    # 2. 조회 요청 (DB에 있는 것과 없는 것 섞어서)
    names_to_search = ["양파", "우유", "없는재료"]
    result = await repo.get_expiry_infos(names_to_search)

    # 3. 검증
    assert len(result) == 2
    assert "양파" in result
    assert "우유" in result
    assert "없는재료" not in result

    assert result["양파"].expiry_day == 7
    assert result["우유"].storage_type == "FRIDGE"


@pytest.mark.asyncio
async def test_add_missing_logs(db_session, test_user):
    """
    [New] 누락 식재료 로그 일괄 저장 테스트
    """
    repo = IngredientRepository(db_session)

    # 1. 로그 객체 생성
    logs = [
        MissingIngredientLog(user_id=test_user.id, ingredient_name="희귀템1"),
        MissingIngredientLog(user_id=test_user.id, ingredient_name="희귀템2"),
    ]

    # 2. 저장 실행
    await repo.add_missing_logs(logs)

    # 3. DB 조회하여 검증
    stmt = select(MissingIngredientLog).where(MissingIngredientLog.user_id == test_user.id)
    saved_logs = (await db_session.execute(stmt)).scalars().all()

    assert len(saved_logs) == 2
    names = [log.ingredient_name for log in saved_logs]
    assert "희귀템1" in names
    assert "희귀템2" in names


@pytest.mark.asyncio
async def test_add_deviation_log(db_session, test_user):
    """
    [New] 유통기한 편차 로그 저장 테스트 (storage_type 포함)
    """
    repo = IngredientRepository(db_session)

    log = ExpiryDeviationLog(
        user_id=test_user.id,
        ingredient_name="감자",
        deviation_day=5,
        storage_type="FROZEN",  # 유저가 선택한 보관타입
    )

    # 1. 저장 실행
    await repo.add_deviation_log(log)

    # 2. DB 조회하여 검증
    stmt = select(ExpiryDeviationLog).where(ExpiryDeviationLog.user_id == test_user.id)
    saved_log = (await db_session.execute(stmt)).scalar_one()

    assert saved_log.ingredient_name == "감자"
    assert saved_log.deviation_day == 5
    assert saved_log.storage_type == "FROZEN"


@pytest.mark.asyncio
async def test_add_and_get_ingredient(db_session, test_user):
    """[Basic] 식재료 저장 및 단일 조회"""
    repo = IngredientRepository(db_session)

    ingredients = [Ingredient(user_id=test_user.id, ingredient_name="기본재료", purchase_date=TODAY)]

    # 저장
    saved_list = await repo.add_ingredients(ingredients)
    saved_id = saved_list[0].id

    # 조회
    found = await repo.get_ingredient(saved_id, test_user.id)
    assert found is not None
    assert found.ingredient_name == "기본재료"


@pytest.mark.asyncio
async def test_update_ingredient_partial(db_session, test_user):
    """
    [Update] 부분 수정 테스트 (update_ingredient)
    - purchase_date만 수정하고 나머지는 유지되는지 확인
    """
    repo = IngredientRepository(db_session)

    # 1. 초기 데이터 저장
    ing = Ingredient(
        user_id=test_user.id,
        ingredient_name="수정전",
        purchase_date=TODAY,
        storage_type="ROOM",
    )
    db_session.add(ing)
    await db_session.commit()
    await db_session.refresh(ing)

    # 2. 부분 수정 요청 (구매일만 변경, 나머지는 None)
    new_date = TODAY + timedelta(days=1)
    updated = await repo.update_ingredient(
        ingredient_id=ing.id,
        user_id=test_user.id,
        purchase_date=new_date,
        expiration_date=None,  # 변경 안 함
        storage_type=None,  # 변경 안 함
    )

    # 3. 검증
    assert updated.purchase_date == new_date
    assert updated.storage_type == "ROOM"  # 기존 값 유지


@pytest.mark.asyncio
async def test_get_ingredients_filtering(db_session, test_user):
    """[Filter] 목록 조회 필터링 (미분류 vs 보관장소별)"""
    repo = IngredientRepository(db_session)

    # 1. 데이터 준비
    # A: 미분류 (보관장소/유통기한 없음)
    i1 = Ingredient(user_id=test_user.id, ingredient_name="미분류", purchase_date=TODAY)
    # B: 냉장 보관
    i2 = Ingredient(
        user_id=test_user.id,
        ingredient_name="냉장",
        purchase_date=TODAY,
        storage_type="FRIDGE",
        expiration_date=TODAY,
    )

    await repo.add_ingredients([i1, i2])

    # 2. 미분류 조회 테스트
    unclassified = await repo.get_ingredients(test_user.id, is_unclassified=True)
    assert len(unclassified) == 1
    assert unclassified[0].ingredient_name == "미분류"

    # 3. 냉장 조회 테스트
    fridge_items = await repo.get_ingredients(test_user.id, storage="FRIDGE")
    assert len(fridge_items) == 1
    assert fridge_items[0].ingredient_name == "냉장"


@pytest.mark.asyncio
async def test_get_unassigned_ingredients_logic(db_session, test_user):
    """
    [Compartment] 미분류(냉장고 칸 미배정) 식재료 조회
    - 조건: compartment_id IS NULL
    """
    repo = IngredientRepository(db_session)

    # 1. 냉장고 및 칸 생성 (스키마 필수 필드 pos_x, pos_y, order_index 포함)
    fridge = Refrigerator(user_id=test_user.id, name="테스트냉장고", pos_x=1, pos_y=1)
    db_session.add(fridge)
    await db_session.commit()
    await db_session.refresh(fridge)

    comp = Compartment(refrigerator_id=fridge.id, name="야채칸", order_index=1)
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    # 2. 식재료 준비
    unassigned_ing = Ingredient(
        user_id=test_user.id,
        ingredient_name="칸없음",
        purchase_date=TODAY,
        compartment_id=None,
    )
    assigned_ing = Ingredient(
        user_id=test_user.id,
        ingredient_name="칸있음",
        purchase_date=TODAY,
        compartment_id=comp.id,
    )

    await repo.add_ingredients([unassigned_ing, assigned_ing])

    # 3. 조회 및 검증
    results = await repo.get_unassigned_ingredients(test_user.id)

    assert len(results) == 1
    assert results[0].ingredient_name == "칸없음"


@pytest.mark.asyncio
async def test_bulk_update_compartment(db_session, test_user):
    """[Compartment] 일괄 이동 테스트"""
    repo = IngredientRepository(db_session)

    # 1. 냉장고/칸 생성
    fridge = Refrigerator(user_id=test_user.id, name="Main", pos_x=0, pos_y=0)
    db_session.add(fridge)
    await db_session.commit()
    await db_session.refresh(fridge)

    comp = Compartment(refrigerator_id=fridge.id, name="1칸", order_index=0)
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    # 2. 재료 준비
    ing1 = Ingredient(user_id=test_user.id, ingredient_name="A", purchase_date=TODAY)
    ing2 = Ingredient(user_id=test_user.id, ingredient_name="B", purchase_date=TODAY)
    await repo.add_ingredients([ing1, ing2])

    # 3. 이동 실행
    count = await repo.bulk_update_compartment([ing1.id, ing2.id], comp.id, test_user.id)

    # 4. 검증
    assert count == 2
    await db_session.refresh(ing1)
    assert ing1.compartment_id == comp.id


@pytest.mark.asyncio
async def test_delete_ingredient(db_session, test_user):
    """[Delete] Soft Delete 테스트"""
    repo = IngredientRepository(db_session)

    ing = Ingredient(user_id=test_user.id, ingredient_name="삭제대상", purchase_date=TODAY)
    db_session.add(ing)
    await db_session.commit()

    # 삭제
    success = await repo.delete_ingredient(ing.id, test_user.id)
    assert success is True

    # 조회 시 없어야 함
    found = await repo.get_ingredient(ing.id, test_user.id)
    assert found is None

    # 실제 DB에는 남아있어야 함 (deleted_at 확인)
    stmt = select(Ingredient).where(Ingredient.id == ing.id)
    real_row = (await db_session.execute(stmt)).scalar_one()
    assert real_row.deleted_at is not None
