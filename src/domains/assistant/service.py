from domains.assistant.llm_handler import LLMHandler
from domains.assistant.schemas import DetailRecipeRequest
from domains.assistant.exceptions import InvalidAIRequestException
from domains.ingredient.repository import IngredientRepository
from domains.user.models import User


class AssistantService:
    def __init__(
        self,
        user: User,
        llm_handler: LLMHandler,
        ingredient_repo: IngredientRepository,
    ):
        self.user = user
        self.llm_handler = llm_handler
        self.ingredient_repo = ingredient_repo

    async def recommend_menus(self):
        ingredients_objects = await self.ingredient_repo.get_ingredients(
            user_id=self.user.id
        )

        if not ingredients_objects:
            raise InvalidAIRequestException(
                "냉장고에 재료가 하나도 없어요! 재료를 먼저 등록해주세요."
            )

        ingredient_names = [i.ingredient_name for i in ingredients_objects]
        return await self.llm_handler.recommend_menus(ingredient_names)

    async def generate_recipe_detail(self, request: DetailRecipeRequest):
        return await self.llm_handler.generate_detail(
            food=request.food, ingredients=request.use_ingredients
        )

    async def search_recipe(self, food_name: str):
        if not food_name or not food_name.strip():
            raise InvalidAIRequestException("요리명을 입력해주세요.")

        return await self.llm_handler.search_recipe(food_name)

    async def get_quick_recipe(self, chat: str):
        if not chat or not chat.strip():
            raise InvalidAIRequestException("재료나 상황을 입력해주세요.")

        return await self.llm_handler.quick_recipe(chat)
