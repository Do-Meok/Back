import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from domains.shopping.repository import ShoppingRepository
from domains.shopping.models import Shopping


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def shopping_repo(mock_session):
    return ShoppingRepository(session=mock_session)


@pytest.mark.asyncio
async def test_add_item(shopping_repo, mock_session):
    # Given
    item = Shopping(user_id=1, item="양파")

    # When
    result = await shopping_repo.add_item(item)

    # Then
    mock_session.add.assert_called_once_with(item)
    mock_session.commit.assert_awaited_once()
    assert result.item == "양파"


@pytest.mark.asyncio
async def test_get_items(shopping_repo, mock_session):
    # Given
    mock_item = Shopping(id=1, user_id=1, item="우유", status=False)

    # SQLAlchemy 결과 체이닝 Mocking (execute -> scalars -> all)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_item]
    mock_session.execute.return_value = mock_result

    # When
    result = await shopping_repo.get_items(user_id=1)

    # Then
    mock_session.execute.assert_awaited_once()
    assert len(result) == 1
    assert result[0].item == "우유"


@pytest.mark.asyncio
async def test_delete_item_success(shopping_repo, mock_session):
    # Given
    mock_result = MagicMock()
    mock_result.rowcount = 1  # 삭제된 행이 1개라고 가정
    mock_session.execute.return_value = mock_result

    # When
    result = await shopping_repo.delete_item(shopping_id=1, user_id=1)

    # Then
    mock_session.commit.assert_awaited_once()
    assert result is True


@pytest.mark.asyncio
async def test_delete_item_failure(shopping_repo, mock_session):
    # Given
    mock_result = MagicMock()
    mock_result.rowcount = 0  # 삭제된 행이 0개
    mock_session.execute.return_value = mock_result

    # When
    result = await shopping_repo.delete_item(shopping_id=999, user_id=1)

    # Then
    mock_session.commit.assert_awaited_once()
    assert result is False
