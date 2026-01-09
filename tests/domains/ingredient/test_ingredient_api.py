import pytest
from datetime import date, timedelta

# 테스트용 데이터 상수
TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
NEXT_WEEK = TODAY + timedelta(days=7)


@pytest.mark.asyncio
async def test_add_ingredient_success(authorized_client):
    # 식재료 추가 테스트
    payload = {"ingredients": ["사과", "돼지고기", "양파"], "purchase_date": str(TODAY)}

    response = await authorized_client.post("/api/v1/ingredients", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    assert data[0]["ingredient_name"] == "사과"
    assert data[1]["ingredient_name"] == "돼지고기"
    assert data[2]["ingredient_name"] == "양파"
    assert data[0]["purchase_date"] == str(TODAY)


@pytest.mark.asyncio
async def test_set_ingredient_details(authorized_client):
    # 식재료 보관장소 및 유통기한 설정 (PATCH /{id})
    # 1. 식재료 추가
    create_res = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["우유"], "purchase_date": str(TODAY)},
    )
    ingredient_id = create_res.json()[0]["id"]

    # 2. 상세 정보 설정 요청
    payload = {"expiration_date": str(NEXT_WEEK), "storage_type": "FRIDGE"}
    response = await authorized_client.patch(
        f"/api/v1/ingredients/{ingredient_id}", json=payload
    )

    # 3. 검증
    assert response.status_code == 200
    data = response.json()
    assert data["expiration_date"] == str(NEXT_WEEK)
    assert data["storage_type"] == "FRIDGE"


@pytest.mark.asyncio
async def test_get_ingredients_filter(authorized_client):
    """
    3. 식재료 목록 조회 (필터링 테스트)
       - 전체 조회
       - 미분류(보관장소 X) 조회
       - 보관장소별 조회
    """
    # [준비]
    # 1) 미분류 식재료 1개 추가 ("감자")
    await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["감자"], "purchase_date": str(TODAY)},
    )

    # 2) 냉장 식재료 1개 추가 및 설정 ("콜라")
    res = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["콜라"], "purchase_date": str(TODAY)},
    )
    cola_id = res.json()[0]["id"]
    await authorized_client.patch(
        f"/api/v1/ingredients/{cola_id}",
        json={"expiration_date": str(NEXT_WEEK), "storage_type": "FRIDGE"},
    )

    # [Case A] 전체 조회 (쿼리 파라미터 없음)
    res_all = await authorized_client.get("/api/v1/ingredients")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2  # 감자, 콜라

    # [Case B] 미분류 조회 (is_unclassified=true) -> "감자"만 나와야 함
    res_unclassified = await authorized_client.get(
        "/api/v1/ingredients?is_unclassified=true"
    )
    assert res_unclassified.status_code == 200
    data = res_unclassified.json()
    assert len(data) == 1
    assert data[0]["ingredient_name"] == "감자"
    assert data[0]["storage_type"] is None

    # [Case C] 냉장 보관 조회 (storage=FRIDGE) -> "콜라"만 나와야 함
    res_fridge = await authorized_client.get("/api/v1/ingredients?storage=FRIDGE")
    assert res_fridge.status_code == 200
    data = res_fridge.json()
    assert len(data) == 1
    assert data[0]["ingredient_name"] == "콜라"
    assert data[0]["storage_type"] == "FRIDGE"


@pytest.mark.asyncio
async def test_get_ingredient_detail(authorized_client):
    """
    4. 식재료 단일 조회 (GET /detail)
    """
    # 추가
    res = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["당근"], "purchase_date": str(TODAY)},
    )
    carrot_id = res.json()[0]["id"]

    # 조회
    response = await authorized_client.get(
        f"/api/v1/ingredients/detail?ingredient_id={carrot_id}"
    )

    assert response.status_code == 200
    assert response.json()["ingredient_name"] == "당근"


@pytest.mark.asyncio
async def test_update_ingredient(authorized_client):
    """
    5. 식재료 수정 (PATCH /update/{id})
    """
    # 추가
    res = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["오이"], "purchase_date": str(TODAY)},
    )
    cucumber_id = res.json()[0]["id"]

    # 수정 (이름은 그대로, 구매일과 보관장소 변경)
    payload = {"purchase_date": str(TOMORROW), "storage_type": "ROOM"}
    response = await authorized_client.patch(
        f"/api/v1/ingredients/update/{cucumber_id}", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["purchase_date"] == str(TOMORROW)  # 변경됨
    assert data["storage_type"] == "ROOM"  # 변경됨


@pytest.mark.asyncio
async def test_delete_ingredient(authorized_client):
    """
    6. 식재료 삭제 (DELETE)
    """
    # 추가
    res = await authorized_client.post(
        "/api/v1/ingredients",
        json={"ingredients": ["쓰레기"], "purchase_date": str(TODAY)},
    )
    trash_id = res.json()[0]["id"]

    # 삭제
    response = await authorized_client.delete(
        f"/api/v1/ingredients?ingredient_id={trash_id}"
    )
    assert response.status_code == 204

    # 재조회 시 404 발생 확인 (또는 목록에서 안 보여야 함)
    check_res = await authorized_client.get(
        f"/api/v1/ingredients/detail?ingredient_id={trash_id}"
    )
    assert check_res.status_code == 404  # IngredientNotFoundException


@pytest.mark.asyncio
async def test_ingredient_not_found(authorized_client):
    """
    7. 존재하지 않는 ID로 요청 시 404 에러 테스트
    """
    # 없는 ID로 조회
    res = await authorized_client.get("/api/v1/ingredients/detail?ingredient_id=99999")
    assert res.status_code == 404

    # 없는 ID로 수정
    res = await authorized_client.patch(
        "/api/v1/ingredients/99999",
        json={"expiration_date": str(TODAY), "storage_type": "FRIDGE"},
    )
    assert res.status_code == 404

    # 없는 ID로 삭제
    res = await authorized_client.delete("/api/v1/ingredients?ingredient_id=99999")
    assert res.status_code == 404
