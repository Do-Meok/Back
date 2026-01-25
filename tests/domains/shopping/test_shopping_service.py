import pytest
from unittest.mock import AsyncMock
from domains.shopping.service import ShoppingService
from domains.shopping.models import Shopping
from domains.shopping.schemas import AddItemRequest
from domains.shopping.exception import ItemNotFoundException
from domains.user.models import User


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_user():
    return User(id=1, email="test@test.com")


@pytest.fixture
def shopping_service(mock_user, mock_repo):
    return ShoppingService(user=mock_user, shopping_repo=mock_repo)


@pytest.mark.asyncio
async def test_add_item(shopping_service, mock_repo):
    # Given
    request = AddItemRequest(item_name="삼겹살")
    # 레포지토리가 반환할 가짜 객체 설정 (ID가 생성된 상태)
    mock_repo.add_item.return_value = Shopping(id=10, user_id=1, item="삼겹살")

    # When
    response = await shopping_service.add_item(request)

    # Then
    mock_repo.add_item.assert_called_once()
    assert response.id == 10
    assert response.item_name == "삼겹살"


@pytest.mark.asyncio
async def test_get_list(shopping_service, mock_repo):
    # Given
    mock_repo.get_items.return_value = [
        Shopping(id=1, item="사과"),
        Shopping(id=2, item="배")
    ]

    # When
    response = await shopping_service.get_list()

    # Then
    assert len(response) == 2
    assert response[0].item_name == "사과"
    assert response[1].item_name == "배"


@pytest.mark.asyncio
async def test_delete_item_success(shopping_service, mock_repo):
    # Given
    mock_repo.delete_item.return_value = True

    # When
    await shopping_service.delete_item(shopping_id=1)

    # Then (에러 없이 통과하면 성공)
    mock_repo.delete_item.assert_called_once_with(shopping_id=1, user_id=1)


@pytest.mark.asyncio
async def test_delete_item_not_found(shopping_service, mock_repo):
    # Given
    mock_repo.delete_item.return_value = False  # 삭제 실패 상황

    # When & Then
    with pytest.raises(ItemNotFoundException) as excinfo:
        await shopping_service.delete_item(shopping_id=999)

    assert str(excinfo.value.detail) == "삭제할 항목을 찾을 수 없습니다."