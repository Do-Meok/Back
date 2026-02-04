import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from domains.recipe.service import RecipeService
from domains.recipe.schemas import SaveRecipeRequest, SavedRecipeResponse
from domains.recipe.exception import RecipeDataCorruptionException
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
