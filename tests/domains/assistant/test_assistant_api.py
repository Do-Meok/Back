from unittest.mock import AsyncMock

import pytest

from core.di import get_assistant_service
from domains.assistant.exceptions import InvalidAIRequestException
from domains.assistant.schemas import ReceiptIngredientResponse, RecommendationItem, RecommendationResponse
from main import app


# --- Fixtures ---
@pytest.fixture
def mock_assistant_service():
    """AI 서비스 Mock 객체를 생성하는 픽스처"""
    return AsyncMock()


# --- Tests ---
@pytest.mark.asyncio
async def test_get_recommendations_default(authorized_client, mock_assistant_service):
    """[API] GET /assistant/recommendations (기본 호출 - 캐시 사용)"""
    mock_item = RecommendationItem(
        food="가짜요리",
        food_en="Fake Food",
        use_ingredients=["물", "불"],
        difficulty=1,
        image_url="http://fake.com/image.jpg",
    )
    mock_assistant_service.recommend_menus.return_value = RecommendationResponse(recipes=[mock_item])

    app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_service

    try:
        # 쿼리 파라미터 없이 요청
        response = await authorized_client.get("/api/v1/assistant/recommendations")

        assert response.status_code == 200
        data = response.json()

        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["food"] == "가짜요리"
        assert data["recipes"][0]["image_url"] == "http://fake.com/image.jpg"

        # [핵심 검증] 파라미터를 안 넘겼으니 force_refresh=False 로 호출되었는지 확인
        mock_assistant_service.recommend_menus.assert_called_once_with(force_refresh=False)

    finally:
        app.dependency_overrides.pop(get_assistant_service, None)


@pytest.mark.asyncio
async def test_get_recommendations_force_refresh(authorized_client, mock_assistant_service):
    """[API] GET /assistant/recommendations?force_refresh=true (새로고침 - 강제 호출)"""
    mock_assistant_service.recommend_menus.return_value = RecommendationResponse(recipes=[])

    app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_service

    try:
        # 쿼리 파라미터 포함하여 요청
        response = await authorized_client.get("/api/v1/assistant/recommendations?force_refresh=true")

        assert response.status_code == 200

        # [핵심 검증] 새로고침 요청이므로 force_refresh=True 로 서비스가 호출되었는지 확인
        mock_assistant_service.recommend_menus.assert_called_once_with(force_refresh=True)

    finally:
        app.dependency_overrides.pop(get_assistant_service, None)


@pytest.mark.asyncio
async def test_search_recipe_api_validation(authorized_client):
    """[API] POST /assistant/search 유효성 검사 (Pydantic)"""
    # 요청 바디가 스키마(food 필드 필수)와 맞지 않음
    invalid_body = {"wrong_field": "김치찌개"}
    response = await authorized_client.post("/api/v1/assistant/search", json=invalid_body)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_receipt_api_success(authorized_client, mock_assistant_service):
    """[API] POST /receipt/extract 영수증 식재료 추출 성공"""
    mock_assistant_service.process_receipt_image.return_value = ReceiptIngredientResponse(
        ingredients=["콩나물", "두부", "대파"]
    )

    app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_service

    try:
        files = {"file": ("receipt_test.jpg", b"fake_image_bytes", "image/jpeg")}
        response = await authorized_client.post("/api/v1/assistant/receipt/extract", files=files)

        assert response.status_code == 200
        data = response.json()

        assert "ingredients" in data
        assert len(data["ingredients"]) == 3
        assert "콩나물" in data["ingredients"]

    finally:
        app.dependency_overrides.pop(get_assistant_service, None)


@pytest.mark.asyncio
async def test_extract_receipt_api_invalid_file(authorized_client, mock_assistant_service):
    """[API] POST /receipt/extract 실패 (Service 예외 발생)"""
    # Service 메서드 호출 시 InvalidAIRequestException 예외 발생하도록 설정
    mock_assistant_service.process_receipt_image.side_effect = InvalidAIRequestException(
        "이미지 파일만 업로드 가능합니다."
    )

    app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_service

    try:
        files = {"file": ("notes.txt", b"just text", "text/plain")}
        response = await authorized_client.post("/api/v1/assistant/receipt/extract", files=files)

        # 예외 핸들러 설정에 따라 400 상태 코드를 반환한다고 가정
        assert response.status_code in [400, 422]
        data = response.json()

        if "detail" in data:
            assert data["detail"] == "이미지 파일만 업로드 가능합니다."

    finally:
        app.dependency_overrides.pop(get_assistant_service, None)
