from typing import TypeVar

from pydantic import BaseModel, ValidationError

from core.exception.exceptions import UnexpectedException
from domains.assistant.clients import llm_client
from domains.assistant.parser import LLMParser
from domains.assistant.prompt_builder import PromptBuilder
from domains.assistant.schemas import DetailRecipeResponse, ReceiptIngredientResponse, RecommendationResponse

T = TypeVar("T", bound=BaseModel)


class LLMHandler:
    def __init__(self):
        self.client = llm_client

    async def _process(self, prompt: str, response_model: type[T]) -> T:
        raw_text = await self.client.get_response(prompt)
        parsed_dict = LLMParser.parse(raw_text)

        try:
            return response_model(**parsed_dict)

        except ValidationError as e:
            print(f"Schema Error: {e}")
            raise UnexpectedException("AI 응답 형식이 올바르지 않습니다.")

    async def recommend_menus(self, ingredients: list[str]) -> RecommendationResponse:
        prompt = PromptBuilder.build_suggestion_prompt(ingredients)
        return await self._process(prompt, RecommendationResponse)

    async def generate_detail(self, food: str, ingredients: list[dict]) -> DetailRecipeResponse:
        prompt = PromptBuilder.build_recipe_prompt(food, ingredients)
        return await self._process(prompt, DetailRecipeResponse)

    async def search_recipe(self, food_name: str) -> DetailRecipeResponse:
        prompt = PromptBuilder.build_search_prompt(food_name)
        return await self._process(prompt, DetailRecipeResponse)

    async def quick_recipe(self, chat: str) -> DetailRecipeResponse:
        prompt = PromptBuilder.build_quick_prompt(chat)
        return await self._process(prompt, DetailRecipeResponse)

    async def parse_receipt_ingredients(self, ocr_text: str) -> ReceiptIngredientResponse:
        prompt = PromptBuilder.build_receipt_parsing_prompt(ocr_text)
        return await self._process(prompt, ReceiptIngredientResponse)
