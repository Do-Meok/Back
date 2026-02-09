import pytest
from unittest.mock import AsyncMock

from domains.assistant.exceptions import InvalidAIRequestException
from main import app
from core.di import get_assistant_service
from domains.assistant.schemas import RecommendationResponse, RecommendationItem, ReceiptIngredientResponse


async def mock_get_assistant_service():
    mock_service = AsyncMock()
    mock_service.recommend_menus.return_value = RecommendationResponse(
        recipes=[RecommendationItem(food="가짜요리", use_ingredients=["물"], difficulty=1)]
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
    response = await authorized_client.post("/api/v1/assistant/search", json={"wrong_field": "김치찌개"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_receipt_api_success(authorized_client):
    """POST /receipt/extract 영수증 식재료 추출 성공 테스트"""

    # --- [Mock 설정] ---
    # 실제 OCR/LLM을 호출하지 않고, 성공 결과만 반환하도록 서비스 모킹
    async def mock_service_success():
        mock_svc = AsyncMock()
        mock_svc.process_receipt_image.return_value = ReceiptIngredientResponse(ingredients=["콩나물", "두부", "대파"])
        return mock_svc

    app.dependency_overrides[get_assistant_service] = mock_service_success

    # --- [파일 준비] ---
    # ('파일명', b'파일바이너리내용', 'Content-Type') 튜플 형태
    files = {"file": ("receipt_test.jpg", b"fake_image_bytes", "image/jpeg")}

    # --- [API 요청] ---
    # json=... 대신 files=... 를 사용해야 합니다.
    response = await authorized_client.post("/api/v1/assistant/receipt/extract", files=files)

    # --- [검증] ---
    assert response.status_code == 200
    data = response.json()

    assert "ingredients" in data
    assert len(data["ingredients"]) == 3
    assert "콩나물" in data["ingredients"]

    # --- [정리] ---
    del app.dependency_overrides[get_assistant_service]


@pytest.mark.asyncio
async def test_extract_receipt_api_invalid_file(authorized_client):
    """POST /receipt/extract 실패 테스트 (서비스가 예외를 던지는 경우)"""

    # --- [Mock 설정] ---
    async def mock_service_failure():
        mock_svc = AsyncMock()
        # process_receipt_image가 호출되면 예외를 발생시킴
        mock_svc.process_receipt_image.side_effect = InvalidAIRequestException("이미지 파일만 업로드 가능합니다.")
        return mock_svc

    app.dependency_overrides[get_assistant_service] = mock_service_failure

    # --- [파일 준비] ---
    # 텍스트 파일을 보낸다고 가정
    files = {"file": ("notes.txt", b"just text", "text/plain")}

    # --- [API 요청] ---
    response = await authorized_client.post("/api/v1/assistant/receipt/extract", files=files)

    # --- [검증] ---
    # Exception Handler가 400 Bad Request로 변환해서 응답한다고 가정
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "이미지 파일만 업로드 가능합니다."

    # --- [정리] ---
    del app.dependency_overrides[get_assistant_service]
