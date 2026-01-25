import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from main import app  # FastAPI 앱 인스턴스 (main.py에 있다고 가정)
from core.di import get_shopping_service
from domains.shopping.schemas import AddItemResponse, GetItemResponse
from domains.shopping.exception import ItemNotFoundException

# 가짜 서비스를 만드는 픽스처
@pytest.fixture
def mock_shopping_service():
    return AsyncMock()

# FastAPI의 의존성을 가짜 서비스로 바꿔치기하는 픽스처
@pytest.fixture
def client(mock_shopping_service):
    app.dependency_overrides[get_shopping_service] = lambda: mock_shopping_service
    return TestClient(app)

def test_add_item_api(client, mock_shopping_service):
    # Given
    mock_shopping_service.add_item.return_value = AddItemResponse(id=1, item_name="당근")
    payload = {"item_name": "당근"}

    # When
    response = client.post("/api/v1/shopping", json=payload) # URL 경로는 실제 설정에 맞게 수정

    # Then
    assert response.status_code == 201
    assert response.json() == {"id": 1, "item_name": "당근"}

def test_get_list_api(client, mock_shopping_service):
    # Given
    mock_shopping_service.get_list.return_value = [
        GetItemResponse(id=1, item_name="콜라"),
        GetItemResponse(id=2, item_name="사이다")
    ]

    # When
    response = client.get("/api/v1/shopping")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["item_name"] == "콜라"

def test_delete_item_api_success(client, mock_shopping_service):
    # Given
    mock_shopping_service.delete_item.return_value = None  # 리턴값 없음

    # When
    response = client.delete("/api/v1/shopping/1")

    # Then
    assert response.status_code == 204

def test_delete_item_api_not_found(client, mock_shopping_service):
    # Given
    # 서비스가 예외를 던지도록 설정
    mock_shopping_service.delete_item.side_effect = ItemNotFoundException()

    # When
    response = client.delete("/api/v1/shopping/999")

    # Then
    # (주의: 전역 예외 처리기가 설정되어 있다면 404가 나오겠지만,
    # 핸들러가 없으면 500이 나올 수도 있습니다. 핸들러 설정 가정하에 404 체크)
    assert response.status_code == 404