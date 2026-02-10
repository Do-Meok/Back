import asyncio
import httpx

from fastapi import UploadFile
from datetime import datetime, timedelta, time
from redis.asyncio import Redis

from core.config import settings
from domains.assistant.clients import ocr_client
from domains.assistant.llm_handler import LLMHandler
from domains.assistant.schemas import DetailRecipeRequest, DetailRecipeResponse
from domains.assistant.exceptions import InvalidAIRequestException
from domains.ingredient.repository import IngredientRepository
from domains.user.models import User

LIMIT_RECIPE_DAILY = 10  # 하루 레시피 10회
LIMIT_OCR_DAILY = 2  # 하루 영수증 2회


class AssistantService:
    def __init__(self, user: User, llm_handler: LLMHandler, ingredient_repo: IngredientRepository, redis: Redis):
        self.user = user
        self.llm_handler = llm_handler
        self.ingredient_repo = ingredient_repo
        self.redis = redis

    async def _check_limit(self, action_type: str, limit: int):
        today_str = datetime.now().strftime("%Y-%m-%d")
        key = f"limit:{action_type}:{self.user.id}:{today_str}"

        current_count = await self.redis.incr(key)

        if current_count == 1:
            now = datetime.now()
            midnight = datetime.combine(now.date() + timedelta(days=1), time.min)
            seconds_until_midnight = int((midnight - now).total_seconds())
            await self.redis.expire(key, seconds_until_midnight)

        if current_count > limit:
            await self.redis.decr(key)
            raise InvalidAIRequestException(
                f"일일 {action_type} 한도({limit}회)를 초과했습니다. 내일 다시 이용해주세요."
            )

        return current_count

    async def _fetch_unsplash_image(self, query: str) -> str:
        if not settings.UNSPLASH_ACCESS_KEY:
            return "https://via.placeholder.com/600x400?text=No+API+Key"

        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "page": 1,
            "per_page": 1,
            "orientation": "landscape",
            "client_id": settings.UNSPLASH_ACCESS_KEY,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=3.0)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]["urls"]["regular"]
        except Exception as e:
            print(f"Unsplash Error ({query}): {e}")

        return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=60"

    async def _attach_image_url(self, response: DetailRecipeResponse) -> DetailRecipeResponse:
        query = response.food_en if response.food_en else f"{response.food} food"
        response.image_url = await self._fetch_unsplash_image(query)
        return response

    async def recommend_menus(self):
        # ... (기존 코드와 동일) ...
        await self._check_limit("recipe", LIMIT_RECIPE_DAILY)
        ingredients_objects = await self.ingredient_repo.get_ingredients(user_id=self.user.id)
        if not ingredients_objects:
            raise InvalidAIRequestException("냉장고에 재료가 하나도 없어요! 재료를 먼저 등록해주세요.")
        ingredient_names = [i.ingredient_name for i in ingredients_objects]

        response = await self.llm_handler.recommend_menus(ingredient_names)

        tasks = []
        for recipe in response.recipes:
            query = recipe.food_en if recipe.food_en else f"{recipe.food} food"
            tasks.append(self._fetch_unsplash_image(query))
        image_urls = await asyncio.gather(*tasks)

        for recipe, url in zip(response.recipes, image_urls):
            recipe.image_url = url
        return response

    # [수정] 이미지 첨부 로직 추가
    async def generate_recipe_detail(self, request: DetailRecipeRequest):
        await self._check_limit("recipe", LIMIT_RECIPE_DAILY)
        # 1. LLM에게 상세 레시피 요청
        response = await self.llm_handler.generate_detail(food=request.food, ingredients=request.use_ingredients)
        # 2. 이미지 검색 및 첨부 후 반환
        return await self._attach_image_url(response)

    # [수정] 이미지 첨부 로직 추가
    async def search_recipe(self, food_name: str):
        if not food_name or not food_name.strip():
            raise InvalidAIRequestException("요리명을 입력해주세요.")
        await self._check_limit("recipe", LIMIT_RECIPE_DAILY)
        # 1. LLM에게 검색 결과 요청
        response = await self.llm_handler.search_recipe(food_name)
        # 2. 이미지 검색 및 첨부 후 반환
        return await self._attach_image_url(response)

    # [수정] 이미지 첨부 로직 추가
    async def get_quick_recipe(self, chat: str):
        if not chat or not chat.strip():
            raise InvalidAIRequestException("재료나 상황을 입력해주세요.")
        await self._check_limit("recipe", LIMIT_RECIPE_DAILY)
        # 1. LLM에게 퀵 레시피 요청
        response = await self.llm_handler.quick_recipe(chat)
        # 2. 이미지 검색 및 첨부 후 반환
        return await self._attach_image_url(response)

    async def process_receipt_image(self, file: UploadFile):
        if not file or not file.filename:
            raise InvalidAIRequestException("업로드된 파일이 없습니다.")

        if not file.content_type.startswith("image/"):
            raise InvalidAIRequestException("이미지 파일만 업로드 가능합니다.")

        await self._check_limit("ocr", LIMIT_OCR_DAILY)
        content = await file.read()

        if not content:
            raise InvalidAIRequestException("파일 내용이 비어있습니다.")

        ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"

        raw_text = await ocr_client.get_ocr_text(content, ext)

        if not raw_text.strip():
            raise InvalidAIRequestException("영수증에서 글자를 인식하지 못했습니다.")

        result = await self.llm_handler.parse_receipt_ingredients(raw_text)

        return result
