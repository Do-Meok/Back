import pytest
from unittest.mock import AsyncMock, patch

from domains.assistant.llm_handler import LLMHandler
from domains.assistant.schemas import (
    RecommendationResponse,
    ReceiptIngredientResponse,
    DetailRecipeResponse
)
from domains.assistant.exceptions import (
    AIJsonDecodeException,
    AISchemaMismatchException,
    AIRefusalException,
)


@pytest.mark.asyncio
class TestLLMHandler:
    @pytest.fixture
    def handler(self):
        return LLMHandler()

    # 1. 메뉴 추천 테스트
    async def test_recommend_menus_success(self, handler):
        """[성공] 메뉴 추천: JSON -> Pydantic 변환 (food_en 포함)"""
        fake_response = """
        ```json
        {
            "recipes": [
                {
                    "food": "김치찌개",
                    "food_en": "Kimchi Stew",
                    "use_ingredients": ["김치", "돼지고기"],
                    "difficulty": 3
                }
            ]
        }
        ```
        """
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response

            result = await handler.recommend_menus(["김치", "돼지고기"])

            assert isinstance(result, RecommendationResponse)
            assert result.recipes[0].food == "김치찌개"
            assert result.recipes[0].food_en == "Kimchi Stew"
            assert result.recipes[0].difficulty == 3

    # 2. [New] 상세 레시피 테스트
    async def test_generate_detail_success(self, handler):
        """[성공] 상세 레시피: JSON -> DetailRecipeResponse 변환"""
        fake_response = """
        {
            "food": "라면",
            "food_en": "Ramen",
            "use_ingredients": [
                {"name": "면", "amount": "1개"},
                {"name": "스프", "amount": "1봉지"}
            ],
            "steps": ["물을 끓인다.", "면과 스프를 넣는다."],
            "tip": "파를 넣으면 맛있다."
        }
        """
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response

            # args는 테스트용 더미 데이터
            result = await handler.generate_detail("라면", [{"name": "면"}])

            assert isinstance(result, DetailRecipeResponse)
            assert result.food == "라면"
            assert result.food_en == "Ramen"
            assert len(result.use_ingredients) == 2
            assert result.use_ingredients[0].amount == "1개"
            assert len(result.steps) == 2

    # 3. [New] 레시피 검색 테스트
    async def test_search_recipe_success(self, handler):
        """[성공] 레시피 검색: JSON -> DetailRecipeResponse 변환"""
        fake_response = """
        {
            "food": "떡볶이",
            "food_en": "Tteokbokki",
            "use_ingredients": [{"name": "떡", "amount": "200g"}],
            "steps": ["떡을 불린다.", "양념을 넣는다."],
            "tip": "치즈를 추가하세요."
        }
        """
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response

            result = await handler.search_recipe("떡볶이")

            assert isinstance(result, DetailRecipeResponse)
            assert result.food == "떡볶이"
            assert result.food_en == "Tteokbokki"

    # 4. [New] 퀵 레시피 테스트
    async def test_quick_recipe_success(self, handler):
        """[성공] 퀵 레시피: JSON -> DetailRecipeResponse 변환"""
        fake_response = """
        {
            "food": "계란밥",
            "food_en": "Egg Rice",
            "use_ingredients": [{"name": "밥", "amount": "1공기"}],
            "steps": ["밥에 계란을 넣는다."],
            "tip": "간장 필수"
        }
        """
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response

            result = await handler.quick_recipe("배고파")

            assert isinstance(result, DetailRecipeResponse)
            assert result.food == "계란밥"

    # 5. 예외 처리 테스트 (기존 유지)
    async def test_handler_schema_mismatch(self, handler):
        fake_response = '{"wrong_key": "잘못된 데이터"}'
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response
            with pytest.raises(AISchemaMismatchException):
                await handler.recommend_menus(["양파"])

    async def test_handler_json_decode_error(self, handler):
        fake_response = "미안해, 레시피를 못 찾겠어."
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response
            with pytest.raises(AIJsonDecodeException):
                await handler.recommend_menus(["양파"])

    async def test_handler_refusal_error(self, handler):
        fake_response = '{"error": "식재료가 아닙니다."}'
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response
            with pytest.raises(AIRefusalException) as exc:
                await handler.recommend_menus(["벽돌"])
            assert str(exc.value.detail) == "식재료가 아닙니다."

    # 6. 영수증 OCR 테스트 (기존 유지)
    async def test_parse_receipt_ingredients_success(self, handler):
        fake_response = """
        ```json
        { "ingredients": ["삼겹살", "쌈장", "깐마늘"] }
        ```
        """
        ocr_text = "영수증 텍스트..."
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response
            result = await handler.parse_receipt_ingredients(ocr_text)

            assert isinstance(result, ReceiptIngredientResponse)
            assert len(result.ingredients) == 3

    async def test_parse_receipt_ingredients_empty(self, handler):
        fake_response = '{"ingredients": []}'
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response
            result = await handler.parse_receipt_ingredients("쓰레기봉투")

            assert isinstance(result, ReceiptIngredientResponse)
            assert result.ingredients == []

    async def test_parse_receipt_ingredients_schema_error(self, handler):
        fake_response = '{"items": ["사과"]}'
        with patch.object(handler.client, "get_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake_response
            with pytest.raises(AISchemaMismatchException):
                await handler.parse_receipt_ingredients("사과")