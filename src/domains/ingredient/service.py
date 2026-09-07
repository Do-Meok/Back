from core.exception.exceptions import IngredientNotFoundException
from domains.ingredient.model import Ingredient
from domains.ingredient.repository import IngredientRepository
from domains.ingredient.schemas import (
    AddIngredientRequest,
    AddIngredientResponse,
    DeleteIngredientsRequest,
    GetIngredientResponse,
)
from domains.user.model import User


class IngredientService:
    def __init__(self, user: User, ingredient_repo: IngredientRepository):
        self.user = user
        self.ingredient_repo = ingredient_repo

    async def add_ingredients(self, request: AddIngredientRequest) -> list[AddIngredientResponse]:
        ingredients = [
            Ingredient(
                user_id=self.user.id,
                ingredient_name=name,
            )
            for name in request.ingredients
        ]
        saved = await self.ingredient_repo.add_ingredient(ingredients)
        return [AddIngredientResponse.model_validate(item) for item in saved]

    async def get_ingredients(self) -> list[GetIngredientResponse]:
        ingredients = await self.ingredient_repo.get_ingredients(self.user.id)
        return [GetIngredientResponse.model_validate(item) for item in ingredients]

    async def delete_ingredient(self, ingredient_id: int) -> None:
        deleted = await self.ingredient_repo.delete_ingredient(ingredient_id, self.user.id)
        if not deleted:
            raise IngredientNotFoundException()

    async def delete_ingredients(self, request: DeleteIngredientsRequest) -> None:
        ingredient_ids = list(dict.fromkeys(request.ingredient_ids))
        deleted_count = await self.ingredient_repo.delete_ingredients_by_ids(ingredient_ids, self.user.id)
        if deleted_count != len(ingredient_ids):
            raise IngredientNotFoundException("삭제할 식재료 중 존재하지 않는 항목이 있습니다.")

    async def delete_all_ingredients(self) -> None:
        deleted = await self.ingredient_repo.delete_all_ingredients(self.user.id)
        if not deleted:
            raise IngredientNotFoundException("삭제할 식재료가 존재하지 않거나 이미 비어있습니다.")
