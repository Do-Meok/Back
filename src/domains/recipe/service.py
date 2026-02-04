from pydantic import ValidationError

from domains.recipe.exception import RecipeDataCorruptionException
from domains.recipe.repository import RecipeRepository
from domains.recipe.schemas import SaveRecipeRequest, SavedRecipeResponse
from domains.user.models import User


class RecipeService:
    def __init__(self, user: User, recipe_repo: RecipeRepository):
        self.user = user
        self.recipe_repo = recipe_repo

    async def save_recipe(self, request: SaveRecipeRequest) -> SavedRecipeResponse:
        recipe_dict = request.model_dump(mode="json")

        saved_entity = await self.recipe_repo.save_recipe(
            user_id=self.user.id, food_name=request.food, recipe=recipe_dict
        )

        try:
            return SavedRecipeResponse(
                id=saved_entity.id,
                created_at=saved_entity.created_at,
                **saved_entity.recipe,
            )
        except ValidationError:
            raise RecipeDataCorruptionException("레시피 저장 중 데이터 변환 오류가 발생했습니다.")

    async def get_recipes(self) -> list[SavedRecipeResponse]:
        entities = await self.recipe_repo.get_recipes(self.user.id)

        result = []
        for entity in entities:
            dto = SavedRecipeResponse(id=entity.id, created_at=entity.created_at, **entity.recipe)
            result.append(dto)

        return result
