import pytest
from unittest.mock import AsyncMock

from main import app
from core.di import get_assistant_service
from domains.assistant.schemas import RecommendationResponse, RecommendationItem


async def mock_get_assistant_service():
    mock_service = AsyncMock()
    mock_service.recommend_menus.return_value = RecommendationResponse(
        recipes=[
            RecommendationItem(food="가짜요리", use_ingredients=["물"], difficulty=1)
        ]
    )
    return mock_service


@pytest.mark.asyncio
async def test_get_recommendations_api(authorized_client):
    """GET /assistant/recommendations 엔드포인트 테스트"""

    # 1. AI 서비스만 가짜로 교체 (로그인은 authorized_client가 알아서 해결함)
    app.dependency_overrides[get_assistant_service] = mock_get_assistant_service

    # 2. 클라이언트 직접 생성할 필요 없음! 바로 사용
    response = await authorized_client.get("/api/v1/assistant/recommendations")

    assert response.status_code == 200
    data = response.json()
    assert "recipes" in data
    assert data["recipes"][0]["food"] == "가짜요리"

    # 3. 테스트 끝나면 AI 서비스 오버라이드만 해제 (로그인 오버라이드는 픽스처가 알아서 치워줌)
    del app.dependency_overrides[get_assistant_service]


@pytest.mark.asyncio
async def test_search_recipe_api_validation(authorized_client):
    """POST /assistant/search 유효성 검사 테스트 (Pydantic)"""

    # 여기선 get_assistant_service도 필요 없음 (Pydantic단에서 막히는지 볼 거니까)
    # 로그인(get_current_user)은 authorized_client가 이미 처리했음!

    # 1. 바로 요청
    response = await authorized_client.post(
        "/api/v1/assistant/search", json={"wrong_field": "김치찌개"}
    )

    assert response.status_code == 422
