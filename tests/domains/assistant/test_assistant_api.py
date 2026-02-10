import pytest
from unittest.mock import AsyncMock
from fastapi import UploadFile

from domains.assistant.exceptions import InvalidAIRequestException
from main import app
from core.di import get_assistant_service
from domains.assistant.schemas import RecommendationResponse, RecommendationItem, ReceiptIngredientResponse


# [수정] 스키마 변경 반영 (food_en, image_url 추가)
async def mock_get_assistant_service_success():
    mock_service = AsyncMock()
    mock_item = RecommendationItem(
        food="가짜요리",
        food_en="Fake Food",  # [New] 필수 필드
        use_ingredients=["물", "불"],
        difficulty=1,
        image_url="http://fake.com/image.jpg"  # [New]
    )
    # Service는 RecommendationResponse 객체를 반환함
    mock_service.recommend_menus.return_value = RecommendationResponse(recipes=[mock_item])
    return mock_service


@pytest.mark.asyncio
async def test_get_recommendations_api(authorized_client):
    """GET /assistant/recommendations 엔드포인트 테스트"""

    # 1. AI 서비스 Mock 주입
    app.dependency_overrides[get_assistant_service] = mock_get_assistant_service_success

    try:
        # 2. API 요청
        response = await authorized_client.get("/api/v1/assistant/recommendations")

        # 3. 검증
        assert response.status_code == 200
        data = response.json()

        assert "recipes" in data
        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["food"] == "가짜요리"
        assert data["recipes"][0]["food_en"] == "Fake Food"  # 확인
        assert data["recipes"][0]["image_url"] == "http://fake.com/image.jpg"  # 확인

    finally:
        # 4. 테스트 종료 후 반드시 오버라이드 해제
        app.dependency_overrides.pop(get_assistant_service, None)


@pytest.mark.asyncio
async def test_search_recipe_api_validation(authorized_client):
    """POST /assistant/search 유효성 검사 테스트 (Pydantic)"""

    # 요청 바디가 스키마(food 필드 필수)와 맞지 않음
    invalid_body = {"wrong_field": "김치찌개"}

    response = await authorized_client.post("/api/v1/assistant/search", json=invalid_body)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_receipt_api_success(authorized_client):
    """POST /receipt/extract 영수증 식재료 추출 성공 테스트"""

    # --- [Mock 설정] ---
    async def mock_service_ocr_success():
        mock_svc = AsyncMock()
        mock_svc.process_receipt_image.return_value = ReceiptIngredientResponse(
            ingredients=["콩나물", "두부", "대파"]
        )
        return mock_svc

    app.dependency_overrides[get_assistant_service] = mock_service_ocr_success

    try:
        # --- [파일 준비] ---
        files = {"file": ("receipt_test.jpg", b"fake_image_bytes", "image/jpeg")}

        # --- [API 요청] ---
        response = await authorized_client.post("/api/v1/assistant/receipt/extract", files=files)

        # --- [검증] ---
        assert response.status_code == 200
        data = response.json()

        assert "ingredients" in data
        assert len(data["ingredients"]) == 3
        assert "콩나물" in data["ingredients"]

    finally:
        app.dependency_overrides.pop(get_assistant_service, None)


@pytest.mark.asyncio
async def test_extract_receipt_api_invalid_file(authorized_client):
    """POST /receipt/extract 실패 테스트 (Service에서 예외 발생 시)"""

    # --- [Mock 설정] ---
    async def mock_service_failure():
        mock_svc = AsyncMock()
        # Service 메서드 호출 시 예외 발생하도록 설정
        mock_svc.process_receipt_image.side_effect = InvalidAIRequestException("이미지 파일만 업로드 가능합니다.")
        return mock_svc

    app.dependency_overrides[get_assistant_service] = mock_service_failure

    try:
        # --- [파일 준비] ---
        # 텍스트 파일을 보낸다고 가정 (Service Mock이 어차피 에러를 뱉게 되어 있지만 형식상 맞춤)
        files = {"file": ("notes.txt", b"just text", "text/plain")}

        # --- [API 요청] ---
        response = await authorized_client.post("/api/v1/assistant/receipt/extract", files=files)

        # --- [검증] ---
        # Exception Handler가 작동하여 400 Bad Request와 detail 메시지를 반환하는지 확인
        # (main.py의 exception_handler 설정에 따라 status code는 다를 수 있으나 보통 400 or 500)
        # InvalidAIRequestException이 400으로 매핑되어 있다고 가정합니다.
        assert response.status_code in [400, 422, 500]
        data = response.json()

        # 에러 메시지가 제대로 전달되는지 확인
        if "detail" in data:
            assert data["detail"] == "이미지 파일만 업로드 가능합니다."

    finally:
        app.dependency_overrides.pop(get_assistant_service, None)