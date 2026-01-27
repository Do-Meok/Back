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

    async def test_get_unassigned_ingredients(self, mocks):
        """[Service] 미분류 식재료 조회 및 응답 모델 변환"""
        user, repo = mocks
        service = IngredientService(user, repo)

        # Mock Data: Repository가 반환할 Ingredient 객체 리스트
        mock_ing1 = MagicMock(
            id=1,
            ingredient_name="당근",
            purchase_date=TODAY,
            expiration_date=None,
            storage_type=None,
            compartment_id=None
        )
        mock_ing2 = MagicMock(
            id=2,
            ingredient_name="오이",
            purchase_date=TODAY,
            expiration_date=None,
            storage_type=None,
            compartment_id=None
        )

        # Repository 메서드 호출 시 위 리스트 반환 설정
        repo.get_unassigned_ingredients.return_value = [mock_ing1, mock_ing2]

        # Call
        result = await service.get_unassigned_ingredients()

        # Verify
        assert len(result) == 2
        # Pydantic 모델로 변환되었는지 속성 확인
        assert result[0].ingredient_name == "당근"
        assert result[1].ingredient_name == "오이"

        # Repository가 올바른 user_id로 호출되었는지 확인
        repo.get_unassigned_ingredients.assert_called_once_with(user.id)

    async def test_move_ingredients_success(self, mocks):
        """[Service] 식재료 이동 성공 시나리오"""
        user, repo = mocks
        service = IngredientService(user, repo)

        target_compartment_id = 10
        req = MagicMock()
        req.ingredient_ids = [1, 2, 3]

        # Mock 설정
        repo.is_my_compartment.return_value = True  # 내 칸 맞음
        repo.bulk_update_compartment.return_value = 3  # 3개 모두 업데이트 성공

        # Call
        res = await service.move_ingredients(target_compartment_id, req)

        # Verify
        assert res.moved_count == 3
        repo.is_my_compartment.assert_called_once_with(target_compartment_id, user.id)
        repo.bulk_update_compartment.assert_called_once()

    async def test_move_ingredients_forbidden(self, mocks):
        """[Service] 내 냉장고 칸이 아닌 경우 Forbidden 예외"""
        user, repo = mocks
        service = IngredientService(user, repo)

        req = MagicMock()
        req.ingredient_ids = [1]

        # Mock: 내 칸이 아님
        repo.is_my_compartment.return_value = False

        from core.exception.exceptions import HaveNotPermissionException

        with pytest.raises(HaveNotPermissionException):
            await service.move_ingredients(99, req)

    async def test_move_ingredients_count_mismatch(self, mocks):
        """[Service] 요청 ID 수와 실제 업데이트 수가 다르면 NotFound(또는 예외) 처리"""
        user, repo = mocks
        service = IngredientService(user, repo)

        req = MagicMock()
        req.ingredient_ids = [1, 2, 3]  # 3개 요청

        # Mock 설정
        repo.is_my_compartment.return_value = True
        repo.bulk_update_compartment.return_value = 2  # 실제로는 2개만 업데이트됨 (하나가 없거나 삭제됨)

        from domains.ingredient.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await service.move_ingredients(10, req)