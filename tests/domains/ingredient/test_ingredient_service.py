import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, timedelta
from domains.ingredient.service import IngredientService
from domains.ingredient.schemas import (
    AddIngredientRequest,
    SetIngredientRequest,
    StorageType,
    UpdateIngredientRequest,
)
from domains.ingredient.exceptions import ValueNotFoundException, NotFoundException
from core.exception.exceptions import HaveNotPermissionException
from domains.user.models import User

TODAY = date.today()


@pytest.mark.asyncio
class TestIngredientService:
    @pytest.fixture
    def mocks(self):
        user = User(id="user-123")
        repo = AsyncMock()
        return user, repo

    # Helper function to create a proper mock ingredient
    def _create_mock_ingredient(self, id, name, p_date=TODAY, e_date=None, storage=None):
        m = MagicMock()
        m.id = id
        m.ingredient_name = name
        m.purchase_date = p_date
        m.expiration_date = e_date
        m.storage_type = storage
        return m

    async def test_add_ingredient_with_missing_log(self, mocks):
        """[Service] 식재료 추가: DB에 정보가 없으면 MissingLog 저장"""
        user, repo = mocks
        service = IngredientService(user, repo)

        req = AddIngredientRequest(ingredients=["희귀템"], purchase_date=TODAY)

        # [Fix] Mock 속성 설정
        mock_saved = self._create_mock_ingredient(1, "희귀템")
        repo.add_ingredients.return_value = [mock_saved]
        repo.get_expiry_infos.return_value = {}

        await service.add_ingredient(req)

        repo.add_ingredients.assert_called_once()
        repo.add_missing_logs.assert_called_once()

    async def test_add_ingredient_no_missing_log(self, mocks):
        """[Service] 식재료 추가: DB에 정보가 있으면 MissingLog 저장 안 함"""
        user, repo = mocks
        service = IngredientService(user, repo)

        req = AddIngredientRequest(ingredients=["양파"], purchase_date=TODAY)

        mock_saved = self._create_mock_ingredient(1, "양파")
        repo.add_ingredients.return_value = [mock_saved]
        repo.get_expiry_infos.return_value = {"양파": MagicMock()}

        await service.add_ingredient(req)

        repo.add_missing_logs.assert_not_called()

    async def test_set_detail_deviation_log(self, mocks):
        """[Service] 상세 설정: 날짜 편차가 2일 이상이거나 보관타입이 다르면 로그 저장"""
        user, repo = mocks
        service = IngredientService(user, repo)

        ing_id = 1
        # [Fix] FROZEN -> FREEZER (Enum에 정의된 값 사용)
        req = SetIngredientRequest(expiration_date=TODAY + timedelta(days=10), storage_type=StorageType.FREEZER)

        mock_ing = self._create_mock_ingredient(ing_id, "양파", TODAY)
        repo.get_ingredient.return_value = mock_ing

        mock_info = MagicMock(expiry_day=7, storage_type="ROOM")
        repo.get_expiry_infos.return_value = {"양파": mock_info}

        mock_updated = self._create_mock_ingredient(ing_id, "양파", TODAY, req.expiration_date, "FREEZER")
        repo.set_ingredient.return_value = mock_updated

        res = await service.set_expiration_and_storage(ing_id, req)

        repo.add_deviation_log.assert_called_once()
        assert res.is_auto_fillable is True

    async def test_get_ingredients_flag_check(self, mocks):
        """[Service] 목록 조회: is_auto_fillable 플래그가 올바르게 매핑되는지"""
        user, repo = mocks
        service = IngredientService(user, repo)

        # [Fix] Mock 속성 설정
        ing1 = self._create_mock_ingredient(1, "감자")
        ing2 = self._create_mock_ingredient(2, "고구마")
        repo.get_ingredients.return_value = [ing1, ing2]

        repo.get_expiry_infos.return_value = {"감자": MagicMock()}

        res = await service.get_ingredients()

        assert res[0].ingredient_name == "감자"
        assert res[0].is_auto_fillable is True

        assert res[1].ingredient_name == "고구마"
        assert res[1].is_auto_fillable is False

    async def test_get_ingredient_single_flag_check(self, mocks):
        """[Service] 단일 조회: is_auto_fillable 플래그 확인"""
        user, repo = mocks
        service = IngredientService(user, repo)

        mock_ing = self._create_mock_ingredient(1, "감자")
        repo.get_ingredient.return_value = mock_ing
        repo.get_expiry_infos.return_value = {"감자": MagicMock()}

        res = await service.get_ingredient(1)

        assert res.is_auto_fillable is True

    async def test_update_ingredient(self, mocks):
        """[Service] 수정 시에도 is_auto_fillable 반환 확인"""
        user, repo = mocks
        service = IngredientService(user, repo)

        mock_updated = self._create_mock_ingredient(1, "감자")
        repo.update_ingredient.return_value = mock_updated
        repo.get_expiry_infos.return_value = {}

        req = UpdateIngredientRequest(storage_type=StorageType.ROOM)
        res = await service.update_ingredient(1, req)

        assert res.is_auto_fillable is False

    async def test_get_unassigned_ingredients(self, mocks):
        """[Service] 미분류 조회"""
        user, repo = mocks
        service = IngredientService(user, repo)

        mock_ing = self._create_mock_ingredient(1, "대파")
        repo.get_unassigned_ingredients.return_value = [mock_ing]
        repo.get_expiry_infos.return_value = {}

        res = await service.get_unassigned_ingredients()
        assert len(res) == 1
        assert res[0].ingredient_name == "대파"
        assert res[0].is_auto_fillable is False

    # ... (나머지 테스트 메서드 - delete, move, set_auto_expiration 등은 Mock 이슈가 없으므로 기존 유지) ...
    async def test_set_auto_expiration_success(self, mocks):
        user, repo = mocks
        service = IngredientService(user, repo)
        ing_id = 1
        mock_ing = self._create_mock_ingredient(ing_id, "마늘", TODAY)
        repo.get_ingredient.return_value = mock_ing
        mock_info = MagicMock(expiry_day=30, storage_type="FREEZER")
        repo.get_expiry_infos.return_value = {"마늘": mock_info}
        repo.set_ingredient.return_value = MagicMock()
        await service.set_auto_expiration_and_storage(ing_id)
        expected_date = TODAY + timedelta(days=30)
        repo.set_ingredient.assert_called_once_with(ing_id, user.id, expected_date, "FREEZER")

    async def test_set_auto_expiration_fail_no_data(self, mocks):
        user, repo = mocks
        service = IngredientService(user, repo)
        repo.get_ingredient.return_value = self._create_mock_ingredient(1, "희귀템")
        repo.get_expiry_infos.return_value = {}
        with pytest.raises(NotFoundException):
            await service.set_auto_expiration_and_storage(1)

    async def test_set_detail_validation_error(self, mocks):
        user, repo = mocks
        service = IngredientService(user, repo)
        req = SetIngredientRequest(expiration_date=None, storage_type=StorageType.FRIDGE)
        with pytest.raises(ValueNotFoundException):
            await service.set_expiration_and_storage(1, req)

    async def test_delete_ingredient(self, mocks):
        user, repo = mocks
        service = IngredientService(user, repo)
        repo.delete_ingredient.return_value = True
        await service.delete_ingredient(1)
        repo.delete_ingredient.assert_called_once()

    async def test_move_ingredients_success(self, mocks):
        user, repo = mocks
        service = IngredientService(user, repo)
        req = MagicMock()
        req.ingredient_ids = [1, 2]
        repo.is_my_compartment.return_value = True
        repo.bulk_update_compartment.return_value = 2
        res = await service.move_ingredients(100, req)
        assert res.moved_count == 2

    async def test_move_ingredients_fail_permission(self, mocks):
        user, repo = mocks
        service = IngredientService(user, repo)
        repo.is_my_compartment.return_value = False
        with pytest.raises(HaveNotPermissionException):
            await service.move_ingredients(999, MagicMock())
