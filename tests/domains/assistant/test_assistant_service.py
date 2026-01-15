import pytest
from unittest.mock import AsyncMock, MagicMock

from domains.assistant.service import AssistantService
from domains.assistant.exceptions import InvalidAIRequestException
from domains.user.models import User


@pytest.mark.asyncio
class TestAssistantService:
    @pytest.fixture
    def mock_deps(self):
        """테스트에 필요한 가짜 객체들을 한 번에 생성"""
        user = User(id="user-123", email="test@test.com")
        repo = AsyncMock()
        handler = AsyncMock()
        return user, repo, handler

    async def test_recommend_menus_with_ingredients(self, mock_deps):
        """[성공] 재료가 있을 때, 이름을 문자열 리스트로 변환해서 Handler에 전달한다."""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # Given: DB에 재료가 2개 있음
        # (실제 Ingredient 모델 구조에 맞춰 수정 필요)
        mock_ingredients = [
            MagicMock(ingredient_name="양파"),
            MagicMock(ingredient_name="계란"),
        ]
        repo.get_ingredients.return_value = mock_ingredients

        # When
        await service.recommend_menus()

        # Then
        # 1. Repo가 올바른 User ID로 호출되었는지
        repo.get_ingredients.assert_called_once_with(user_id=user.id)
        # 2. Handler에게 ["양파", "계란"] 문자열 리스트가 넘어갔는지 (핵심!)
        handler.recommend_menus.assert_called_once_with(["양파", "계란"])

    async def test_recommend_menus_no_ingredients(self, mock_deps):
        """[실패] 재료가 없으면 Handler를 호출하지 않고 InvalidAIRequestException 발생"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # Given: DB 조회 결과가 빈 리스트
        repo.get_ingredients.return_value = []

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "재료를 먼저 등록해주세요" in str(exc.value.detail)
        # Handler는 호출되지 않아야 함 (비용 절약)
        handler.recommend_menus.assert_not_called()

    async def test_search_recipe_empty_input(self, mock_deps):
        """[실패] 검색어가 비어있으면 예외 발생"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # When & Then
        with pytest.raises(InvalidAIRequestException):
            await service.search_recipe("   ")  # 공백 입력

    async def test_quick_recipe_delegation(self, mock_deps):
        """[성공] 퀵 레시피 요청 시 Handler로 문자열이 잘 전달되는지"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # When
        await service.get_quick_recipe("계란으로 아무거나")

        # Then
        handler.quick_recipe.assert_called_once_with("계란으로 아무거나")
