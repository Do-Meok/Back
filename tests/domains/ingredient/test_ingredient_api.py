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
