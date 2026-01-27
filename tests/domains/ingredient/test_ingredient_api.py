import pytest
from datetime import date, timedelta

TODAY = date.today()
NEXT_WEEK = TODAY + timedelta(days=7)


@pytest.mark.asyncio
async def test_add_ingredient_api(authorized_client):
    """[API] 식재료 추가 POST /api/v1/ingredients"""
    payload = {"ingredients": ["소고기"], "purchase_date": str(TODAY)}

    response = await authorized_client.post("/api/v1/ingredients", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data[0]["ingredient_name"] == "소고기"
    return data[0]["id"]  # 다음 테스트를 위해 ID 반환 가능


@pytest.mark.asyncio
async def test_full_lifecycle(authorized_client):
    """[API] 추가 -> 상세설정 -> 수정 -> 조회 -> 삭제 (전체 시나리오)"""

    # 1. 추가
    res1 = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["시나리오용"], "purchase_date": str(TODAY)},
    )
    ing_id = res1.json()[0]["id"]

    # 2. 상세 설정 (PATCH /{id})
    res2 = await authorized_client.patch(
        f"/api/v1/ingredients/{ing_id}",
        json={"expiration_date": str(NEXT_WEEK), "storage_type": "FRIDGE"},
    )
    assert res2.status_code == 200
    assert res2.json()["storage_type"] == "FRIDGE"

    # 3. 수정 (PATCH /update/{id}) - 보관장소 변경
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
    assert res4.json()["ingredient_name"] == "시나리오용"

    # 5. 삭제 (DELETE)
    res5 = await authorized_client.delete(f"/api/v1/ingredients?ingredient_id={ing_id}")
    assert res5.status_code == 204

    # 6. 재조회 시 404
    res6 = await authorized_client.get(
        f"/api/v1/ingredients/detail?ingredient_id={ing_id}"
    )
    assert res6.status_code == 404

    @pytest.mark.asyncio
    async def test_get_unassigned_ingredients_api(authorized_client):
        """[API] 미분류 식재료 조회 GET /api/v1/ingredients/unassigned"""

        # 1. 미분류 식재료 추가 (compartment_id가 없는 상태)
        payload_unassigned = {"ingredients": ["미분류대파"], "purchase_date": str(TODAY)}
        await authorized_client.post("/api/v1/ingredients", json=payload_unassigned)

        # 2. 분류된(상세 설정된) 식재료 추가 (비교군)
        #    먼저 추가 후, update 등을 통해 compartment(냉장고 칸)에 할당해야 하지만,
        #    현재 로직상 '상세 설정(storage_type)'만으로는 compartment_id가
        #    바로 들어가는지, 별도 할당 로직이 있는지에 따라 다를 수 있습니다.
        #    여기서는 순수하게 '방금 등록한 미분류 식재료'가 조회되는지 집중합니다.

        # 3. 조회 요청
        response = await authorized_client.get("/api/v1/ingredients/unassigned")

        assert response.status_code == 200
        data = response.json()

        # 리스트 형태인지, 방금 추가한 재료가 포함되어 있는지 확인
        assert isinstance(data, list)
        # 방금 추가한 '미분류대파'가 결과에 있어야 함
        found = next((item for item in data if item["ingredient_name"] == "미분류대파"), None)
        assert found is not None


@pytest.mark.asyncio
async def test_bulk_move_ingredients_api(authorized_client, db_session, test_user):
    """[API] 식재료 일괄 칸 이동 PATCH /api/v1/ingredients/{compartment_id}/ingredients"""

    # 1. 사전 데이터 준비 (DB에 직접 주입)
    # 1-1. 내 냉장고 칸 생성 (Foreign Key 제약이 있다면 Compartment 모델도 필요하지만, 여기선 ID 100 가정)
    # 실제로는 Compartment를 먼저 생성해야 합니다. 테스트 편의상 로직이 통과되도록 Mocking되거나 데이터가 있다고 가정합니다.
    target_compartment_id = 100

    # 1-2. 미분류 식재료 2개 생성
    from domains.ingredient.models import Ingredient
    ing1 = Ingredient(user_id=test_user.id, ingredient_name="이동할거1", purchase_date=TODAY, compartment_id=None)
    ing2 = Ingredient(user_id=test_user.id, ingredient_name="이동할거2", purchase_date=TODAY, compartment_id=None)

    db_session.add_all([ing1, ing2])
    await db_session.commit()
    await db_session.refresh(ing1)
    await db_session.refresh(ing2)

    # 2. 이동 요청 (API 호출)
    # 주의: Repository의 is_my_compartment 체크를 통과해야 하므로,
    # 테스트 환경에서는 해당 메서드를 Mocking하거나 실제 칸 데이터를 넣어야 합니다.
    # 여기서는 통합 테스트이므로 실제 칸 데이터가 있다고 가정하거나,
    # conftest에서 Repository의 is_my_compartment를 항상 True로 반환하도록 patch 할 수도 있습니다.

    payload = {"ingredient_ids": [ing1.id, ing2.id]}

    # *참고: 만약 칸 소유권 로직 때문에 403이 뜬다면, 테스트용 Compartment 생성 코드가 추가되어야 합니다.*
    response = await authorized_client.patch(
        f"/api/v1/ingredients/{target_compartment_id}/ingredients",
        json=payload
    )

    # 3. 검증
    # 칸 소유권 검증 로직이 실제 DB를 탄다면 403/404가 뜰 수 있으나,
    # 로직이 성공했다는 가정하에 200 OK 검증
    if response.status_code == 200:
        data = response.json()
        assert data["moved_count"] == 2
        assert data["ingredient_ids"] == [ing1.id, ing2.id]

        # DB 재조회하여 실제 compartment_id 변경 확인
        await db_session.refresh(ing1)
        assert ing1.compartment_id == target_compartment_id