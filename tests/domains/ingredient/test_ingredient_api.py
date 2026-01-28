import pytest
from datetime import date, timedelta
from sqlalchemy import select

from domains.ingredient.models import (
    Ingredient,
    IngredientExpiry,
    ExpiryDeviationLog,
    MissingIngredientLog,
)
from domains.refrigerator.models import Refrigerator, Compartment

TODAY = date.today()
NEXT_WEEK = TODAY + timedelta(days=7)


@pytest.mark.asyncio
async def test_add_ingredient_check_auto_flag(authorized_client, db_session):
    """
    [API] 식재료 추가 시 is_auto_fillable 플래그 확인
    """
    # 1. 메타 데이터 주입 (감자)
    expiry_data = IngredientExpiry(
        ingredient_name="감자", expiry_day=10, storage_type="ROOM"
    )
    db_session.add(expiry_data)
    await db_session.commit()

    # 2. 식재료 추가 요청 (감자, 고구마)
    payload = {"ingredients": ["감자", "고구마"], "purchase_date": str(TODAY)}
    response = await authorized_client.post("/api/v1/ingredients", json=payload)

    assert response.status_code == 201
    data = response.json()

    # 3. 플래그 검증
    potato = next(i for i in data if i["ingredient_name"] == "감자")
    sweet_potato = next(i for i in data if i["ingredient_name"] == "고구마")

    assert potato["is_auto_fillable"] is True
    assert sweet_potato["is_auto_fillable"] is False

    # 4. MissingLog 검증 (고구마)
    stmt = select(MissingIngredientLog).where(
        MissingIngredientLog.ingredient_name == "고구마"
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_set_auto_ingredient_details(authorized_client, db_session, test_user):
    """
    [API] 유통기한 자동 채우기 (PATCH /{id}/auto)
    """
    # 1. 메타 데이터 및 식재료 준비
    expiry_data = IngredientExpiry(
        ingredient_name="우유", expiry_day=7, storage_type="FRIDGE"
    )
    db_session.add(expiry_data)

    ing = Ingredient(user_id=test_user.id, ingredient_name="우유", purchase_date=TODAY)
    db_session.add(ing)
    await db_session.commit()
    await db_session.refresh(ing)

    # 2. 자동 채우기 요청
    response = await authorized_client.patch(f"/api/v1/ingredients/{ing.id}/auto")

    assert response.status_code == 200
    data = response.json()

    # 3. 값 검증
    expected_expiry = (TODAY + timedelta(days=7)).isoformat()
    assert data["storage_type"] == "FRIDGE"
    assert data["expiration_date"] == expected_expiry
    assert data["is_auto_fillable"] is True


@pytest.mark.asyncio
async def test_set_details_with_deviation_log(authorized_client, db_session, test_user):
    """
    [API] 상세 설정 시 편차 발생 -> 로그 저장 확인
    """
    # 1. 메타 데이터 (양파: 실온, 5일)
    db_session.add(
        IngredientExpiry(ingredient_name="양파", expiry_day=5, storage_type="ROOM")
    )

    # 2. 식재료 (양파)
    ing = Ingredient(user_id=test_user.id, ingredient_name="양파", purchase_date=TODAY)
    db_session.add(ing)
    await db_session.commit()
    await db_session.refresh(ing)

    # 3. API 요청 (냉동, 20일 -> 편차 발생!)
    payload = {
        "expiration_date": str(TODAY + timedelta(days=20)),
        "storage_type": "FREEZER",  # [Fix] FROZEN -> FREEZER 로 수정!
    }
    response = await authorized_client.patch(
        f"/api/v1/ingredients/{ing.id}", json=payload
    )

    assert response.status_code == 200  # 성공해야 함

    # 4. DB 로그 확인
    stmt = select(ExpiryDeviationLog).where(
        ExpiryDeviationLog.ingredient_name == "양파",
        ExpiryDeviationLog.user_id == test_user.id,
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()

    assert log is not None
    assert log.storage_type == "FREEZER"  # [Fix] 여기도 확인
    assert log.deviation_day == 15  # |20 - 5|


@pytest.mark.asyncio
async def test_full_lifecycle(authorized_client, db_session):
    """[API] 추가 -> 상세설정 -> 수정 -> 조회 -> 삭제 (전체 시나리오 Regression)"""

    # 1. 추가
    res1 = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["라이프사이클용"], "purchase_date": str(TODAY)},
    )
    assert res1.status_code == 201
    ing_id = res1.json()[0]["id"]
    # Schema에 is_auto_fillable이 추가되었으므로 이제 정상 접근 가능
    assert res1.json()[0]["is_auto_fillable"] is False

    # 2. 상세 설정 (PATCH /{id})
    res2 = await authorized_client.patch(
        f"/api/v1/ingredients/{ing_id}",
        json={"expiration_date": str(NEXT_WEEK), "storage_type": "FRIDGE"},
    )
    assert res2.status_code == 200
    assert res2.json()["storage_type"] == "FRIDGE"

    # 3. 수정 (PATCH /update/{id})
    res3 = await authorized_client.patch(
        f"/api/v1/ingredients/update/{ing_id}", json={"storage_type": "FREEZER"}
    )
    assert res3.status_code == 200
    assert res3.json()["storage_type"] == "FREEZER"

    # 4. 조회 (GET /detail)
    res4 = await authorized_client.get(
        f"/api/v1/ingredients/detail?ingredient_id={ing_id}"
    )
    assert res4.status_code == 200

    # 5. 삭제 (DELETE)
    res5 = await authorized_client.delete(f"/api/v1/ingredients?ingredient_id={ing_id}")
    assert res5.status_code == 204


@pytest.mark.asyncio
async def test_get_unassigned_ingredients_api(authorized_client):
    """[API] 미분류 식재료 조회"""
    # 1. 추가
    payload = {"ingredients": ["미분류대파"], "purchase_date": str(TODAY)}
    await authorized_client.post("/api/v1/ingredients", json=payload)

    # 2. 조회
    response = await authorized_client.get("/api/v1/ingredients/unassigned")
    assert response.status_code == 200

    data = response.json()
    found = next(
        (item for item in data if item["ingredient_name"] == "미분류대파"), None
    )
    assert found is not None
    assert found["is_auto_fillable"] is False


@pytest.mark.asyncio
async def test_bulk_move_ingredients_api(authorized_client, db_session, test_user):
    """[API] 식재료 일괄 칸 이동"""

    # 1. 냉장고/칸 생성 (DB 제약조건 준수)
    fridge = Refrigerator(user_id=test_user.id, name="TestFridge", pos_x=0, pos_y=0)
    db_session.add(fridge)
    await db_session.commit()
    await db_session.refresh(fridge)

    comp = Compartment(refrigerator_id=fridge.id, name="TestComp", order_index=0)
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    target_compartment_id = comp.id

    # 2. 식재료 생성
    ing1 = Ingredient(user_id=test_user.id, ingredient_name="A", purchase_date=TODAY)
    ing2 = Ingredient(user_id=test_user.id, ingredient_name="B", purchase_date=TODAY)
    db_session.add_all([ing1, ing2])
    await db_session.commit()
    await db_session.refresh(ing1)
    await db_session.refresh(ing2)

    # 3. 이동 요청
    payload = {"ingredient_ids": [ing1.id, ing2.id]}
    response = await authorized_client.patch(
        f"/api/v1/ingredients/{target_compartment_id}/ingredients", json=payload
    )

    # 4. 검증
    assert response.status_code == 200
    data = response.json()
    assert data["moved_count"] == 2

    await db_session.refresh(ing1)
    assert ing1.compartment_id == target_compartment_id
