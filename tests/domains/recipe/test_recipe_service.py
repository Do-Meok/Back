from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domains.recipe.exception import RecipeDataCorruptionException
from domains.recipe.schemas import SavedRecipeResponse, SaveRecipeRequest
from domains.recipe.service import RecipeService
from domains.user.models import User


@pytest.mark.asyncio
class TestRecipeService:
    @pytest.fixture
    def mocks(self):
        user = User(id="user-123")
        repo = AsyncMock()
        return user, repo

    async def test_save_recipe_success(self, mocks):
        """[Service] 저장 성공 및 Pydantic 변환 테스트"""
        user, repo = mocks
        service = RecipeService(user, repo)

        # Given: 요청 데이터
        request_dto = SaveRecipeRequest(
            food="떡볶이",
            use_ingredients=[],
            steps=["떡을 넣는다"],
            tip="맵게",
            difficulty=2,
        )

        # Mock Repo가 반환할 Entity 설정
        mock_entity = MagicMock()
        mock_entity.id = 1
        mock_entity.created_at = datetime.now()
        # ★ 핵심: Repo는 dict 형태로 데이터를 들고 있음
        mock_entity.recipe = request_dto.model_dump(mode="json")

        repo.save_recipe.return_value = mock_entity

        # When
        result = await service.save_recipe(request_dto)

        # Then
        repo.save_recipe.assert_called_once()
        assert isinstance(result, SavedRecipeResponse)
        assert result.food == "떡볶이"
        assert result.id == 1

    async def test_save_recipe_data_corruption(self, mocks):
        """[Service] DB 저장 후 스키마 불일치 시 예외 발생 테스트"""
        user, repo = mocks
        service = RecipeService(user, repo)

        # Given
        request_dto = SaveRecipeRequest(food="이상한요리", use_ingredients=[], steps=[], tip="", difficulty=1)

        # Mock Repo가 반환할 Entity (필수 필드 누락시킴)
        bad_entity = MagicMock()
        bad_entity.id = 1
        bad_entity.created_at = datetime.now()
        # ❌ 'food' 필드를 일부러 빼버림 -> Pydantic 변환 시 에러 유발
        bad_entity.recipe = {"tip": "이건 필드가 부족해"}

        repo.save_recipe.return_value = bad_entity

        # When & Then
        with pytest.raises(RecipeDataCorruptionException):
            await service.save_recipe(request_dto)

    async def test_get_recipes_success(self, mocks):
        """[Service] 레시피 전체 조회 성공 테스트"""
        user, repo = mocks
        service = RecipeService(user, repo)

        # Given: Repo가 반환할 가짜 Entity 리스트 준비
        mock_entity1 = MagicMock()
        mock_entity1.id = 1
        mock_entity1.created_at = datetime.now()
        mock_entity1.recipe = {"food": "김치찌개", "use_ingredients": [], "steps": [], "tip": "", "difficulty": 1}

        mock_entity2 = MagicMock()
        mock_entity2.id = 2
        mock_entity2.created_at = datetime.now()
        mock_entity2.recipe = {"food": "된장찌개", "use_ingredients": [], "steps": [], "tip": "", "difficulty": 2}

        repo.get_recipes.return_value = [mock_entity1, mock_entity2]

        # When
        result = await service.get_recipes()

        # Then
        repo.get_recipes.assert_called_once_with(user.id)
        assert len(result) == 2
        assert result[0].food == "김치찌개"
        assert result[1].food == "된장찌개"
        assert result[0].id == 1
        assert result[1].id == 2

    async def test_delete_recipe_success(self, mocks):
        """[Service] 레시피 삭제 성공 테스트"""
        user, repo = mocks
        service = RecipeService(user, repo)

        # Given: 내 소유의 레시피 Entity
        mock_entity = MagicMock()
        mock_entity.id = 10
        mock_entity.user_id = user.id  # 현재 유저와 동일한 ID

        repo.get_recipe_by_id.return_value = mock_entity

        # When
        await service.delete_recipe(10)

        # Then
        repo.get_recipe_by_id.assert_called_once_with(10)
        repo.delete_recipe.assert_called_once_with(mock_entity)

    async def test_delete_recipe_not_found(self, mocks):
        """[Service] 존재하지 않는 레시피 삭제 시 예외 발생 테스트"""
        from domains.recipe.exception import RecipeNotFoundException

        user, repo = mocks
        service = RecipeService(user, repo)

        # Given: 조회 결과가 None
        repo.get_recipe_by_id.return_value = None

        # When & Then
        with pytest.raises(RecipeNotFoundException) as exc_info:
            await service.delete_recipe(999)

        # 예외 메시지에 권한 관련 내용이 포함되지 않았는지 확인 (순수 404 에러인지)
        if hasattr(exc_info.value, "detail") and exc_info.value.detail:
            assert "권한" not in exc_info.value.detail

        repo.delete_recipe.assert_not_called()  # 삭제 로직이 호출되지 않아야 함

    async def test_delete_recipe_forbidden(self, mocks):
        """[Service] 타인의 레시피 삭제 시 권한 예외 발생 테스트"""
        from domains.recipe.exception import RecipeNotFoundException

        user, repo = mocks
        service = RecipeService(user, repo)

        # Given: 다른 유저 소유의 레시피 Entity
        mock_entity = MagicMock()
        mock_entity.id = 10
        mock_entity.user_id = "other-user-999"  # 현재 유저와 다른 ID

        repo.get_recipe_by_id.return_value = mock_entity

        # When & Then
        with pytest.raises(RecipeNotFoundException) as exc_info:
            await service.delete_recipe(10)

        # 권한 관련 에러 메시지가 제대로 담겼는지 확인
        assert hasattr(exc_info.value, "detail")
        assert exc_info.value.detail == "삭제 권한이 없습니다."

        repo.delete_recipe.assert_not_called()  # 삭제 로직이 호출되지 않아야 함
