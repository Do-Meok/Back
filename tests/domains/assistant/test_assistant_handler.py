import pytest
from unittest.mock import AsyncMock, patch

from domains.assistant.llm_handler import LLMHandler
from domains.assistant.schemas import RecommendationResponse
from domains.assistant.exceptions import (
    AIJsonDecodeException,
    AISchemaMismatchException,
    AIRefusalException,
)


@pytest.mark.asyncio
class TestLLMHandler:
    @pytest.fixture
    def handler(self):
        # Client를 Mocking한 Handler 생성
        return LLMHandler()

    async def test_recommend_menus_success(self, handler):
        """[성공] 정상적인 JSON 응답이 오면 Pydantic 객체로 변환된다."""

        # Given: AI가 줄 가짜 응답 (Markdown 코드블록 포함)
        fake_response = """
        ```json
        {
            "recipes": [
                {"food": "김치찌개", "use_ingredients": ["김치", "돼지고기"], "difficulty": 3}
            ]
        }
        ```
        """

        # Client의 get_response 메서드를 Mocking (가로채기)
        with patch.object(
            handler.client, "get_response", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = fake_response

            # When
            result = await handler.recommend_menus(["김치", "돼지고기"])

            # Then
            assert isinstance(result, RecommendationResponse)
            assert result.recipes[0].food == "김치찌개"
            assert result.recipes[0].difficulty == 3

    async def test_handler_schema_mismatch(self, handler):
        """[실패] AI가 필수 필드(recipes)를 빼먹고 주면 AISchemaMismatchException 발생"""

        # Given: 'recipes' 키가 없는 엉뚱한 JSON
        fake_response = '{"wrong_key": "잘못된 데이터"}'

        with patch.object(
            handler.client, "get_response", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = fake_response

            # When & Then
            with pytest.raises(AISchemaMismatchException):
                await handler.recommend_menus(["양파"])

    async def test_handler_json_decode_error(self, handler):
        """[실패] JSON이 아닌 평문을 주면 AIJsonDecodeException 발생"""

        # Given: JSON 형식이 아님
        fake_response = "미안해, 레시피를 못 찾겠어."

        with patch.object(
            handler.client, "get_response", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = fake_response

            # When & Then
            with pytest.raises(AIJsonDecodeException):
                await handler.recommend_menus(["양파"])

    async def test_handler_refusal_error(self, handler):
        """[실패] AI가 명시적으로 error 필드를 보내면 AIRefusalException 발생"""

        # Given: 거부 메시지 JSON
        fake_response = '{"error": "식재료가 아닙니다."}'

        with patch.object(
            handler.client, "get_response", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = fake_response

            # When & Then
            with pytest.raises(AIRefusalException) as exc:
                await handler.recommend_menus(["벽돌"])

            assert str(exc.value.detail) == "식재료가 아닙니다."
