import pytest


@pytest.mark.asyncio
async def test_save_recipe_api(authorized_client):
    """[API] POST /api/v1/recipes 저장 테스트"""

    # Given: AI가 줬다고 가정한 JSON payload
    payload = {
        "food": "된장찌개",
        "use_ingredients": [
            {"name": "두부", "amount": "1모"},
            {"name": "된장", "amount": "2스푼"},
        ],
        "steps": ["물을 끓인다", "된장을 푼다", "두부를 넣는다"],
        "tip": "오래 끓이세요",
        "difficulty": 2,
    }

    # When
    response = await authorized_client.post("/api/v1/recipes", json=payload)

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["food"] == "된장찌개"
    assert "id" in data  # 저장된 ID가 있어야 함
    assert "created_at" in data  # 생성 일시가 있어야 함


@pytest.mark.asyncio
async def test_get_recipes_api(authorized_client):
    """[API] GET /api/v1/recipes 조회 테스트"""

    # Given: 미리 하나 저장 (위의 테스트와 독립적)
    await authorized_client.post(
        "/api/v1/recipes",
        json={
            "food": "테스트요리",
            "use_ingredients": [],
            "steps": [],
            "tip": "",
            "difficulty": 1,
        },
    )

    # When
    response = await authorized_client.get("/api/v1/recipes")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["food"] == "테스트요리"


@pytest.mark.asyncio
async def test_delete_recipe_api_success(authorized_client):
    """[API] DELETE /api/v1/recipes/{recipe_id} 삭제 성공 테스트"""

    # Given: 삭제할 레시피를 먼저 생성
    post_response = await authorized_client.post(
        "/api/v1/recipes",
        json={
            "food": "삭제할 요리",
            "use_ingredients": [],
            "steps": ["삭제를 위한 테스트 데이터입니다."],
            "tip": "",
            "difficulty": 1,
        },
    )
    assert post_response.status_code == 201
    recipe_id = post_response.json()["id"]

    # When: 해당 레시피 삭제 요청
    delete_response = await authorized_client.delete(f"/api/v1/recipes/{recipe_id}")

    # Then: 204 No Content 확인
    assert delete_response.status_code == 204

    # 검증: 실제로 삭제되었는지 전체 목록을 조회하여 확인
    get_response = await authorized_client.get("/api/v1/recipes")
    recipes = get_response.json()
    assert not any(r["id"] == recipe_id for r in recipes)


@pytest.mark.asyncio
async def test_delete_recipe_api_not_found(authorized_client):
    """[API] DELETE /api/v1/recipes/{recipe_id} 존재하지 않는 레시피 삭제 시도 테스트"""

    # Given: 존재하지 않는 임의의 레시피 ID
    invalid_recipe_id = 9999999

    # When: 삭제 요청
    response = await authorized_client.delete(f"/api/v1/recipes/{invalid_recipe_id}")

    # Then: RecipeNotFoundException에 매핑된 에러 코드 확인 (설정에 따라 404일 확률이 높음)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_save_recipe_api_validation_error(authorized_client):
    """[API] POST /api/v1/recipes 필수 데이터 누락에 의한 422 검증 에러 테스트"""

    # Given: Pydantic 스키마상 필수일 것으로 예상되는 'food' 필드를 누락한 페이로드
    invalid_payload = {
        # "food": "누락됨",
        "use_ingredients": [{"name": "두부", "amount": "1모"}],
        "steps": ["물을 끓인다"],
        "tip": "오래 끓이세요",
        "difficulty": 2,
    }

    # When: 잘못된 데이터로 저장 요청
    response = await authorized_client.post("/api/v1/recipes", json=invalid_payload)

    # Then: 422 Unprocessable Entity 에러가 발생해야 함
    assert response.status_code == 422
    assert "detail" in response.json()
