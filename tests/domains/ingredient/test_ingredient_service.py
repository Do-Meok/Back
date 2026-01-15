import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from domains.ingredient.service import IngredientService
from domains.ingredient.schemas import (
    AddIngredientRequest,
    SetIngredientRequest,
    StorageType,
    UpdateIngredientRequest,
)
from domains.ingredient.exceptions import (
    IngredientNotFoundException,
    ValueNotFoundException,
)
from domains.user.models import User

TODAY = date.today()


@pytest.mark.asyncio
class TestIngredientService:
    @pytest.fixture
    def mocks(self):
        user = User(id="user-123")
        repo = AsyncMock()
        return user, repo

    async def test_add_ingredient(self, mocks):
        """[Service] 식재료 추가 로직"""
        user, repo = mocks
        service = IngredientService(user, repo)

        req = AddIngredientRequest(ingredients=["사과"], purchase_date=TODAY)

        # Mock 반환값 설정
        mock_ing = MagicMock(id=1, ingredient_name="사과", purchase_date=TODAY)
        repo.add_ingredients.return_value = [mock_ing]

        # Call
        res = await service.add_ingredient(req)

        # Verify
        assert len(res) == 1
        assert res[0].ingredient_name == "사과"
        repo.add_ingredients.assert_called_once()

    async def test_set_detail_validation_error(self, mocks):
        """[Service] 초기 설정 시 필수값 누락 예외 발생"""
        user, repo = mocks
        service = IngredientService(user, repo)

        # 날짜 누락
        req = SetIngredientRequest(
            expiration_date=None, storage_type=StorageType.FRIDGE
        )

        with pytest.raises(ValueNotFoundException):
            await service.set_expiration_and_storage(1, req)

    async def test_update_ingredient_not_found(self, mocks):
        """[Service] 수정 시 존재하지 않는 ID면 예외 발생"""
        user, repo = mocks
        service = IngredientService(user, repo)

        # Repository가 None 반환 (수정 실패)
        repo.update_ingredient.return_value = None

        req = UpdateIngredientRequest(storage_type=StorageType.ROOM)

        with pytest.raises(IngredientNotFoundException):
            await service.update_ingredient(999, req)

    async def test_delete_ingredient_not_found(self, mocks):
        """[Service] 삭제 실패 시 예외 발생"""
        user, repo = mocks
        service = IngredientService(user, repo)

        repo.delete_ingredient.return_value = False  # 삭제된 행 0개

        with pytest.raises(IngredientNotFoundException):
            await service.delete_ingredient(999)
