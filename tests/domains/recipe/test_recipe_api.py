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
