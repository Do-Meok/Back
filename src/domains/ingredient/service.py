from typing import List

from domains.ingredient.repository import IngredientRepository
from domains.user.models import User
from domains.ingredient.schemas import AddIngredientRequest, AddIngredientResponse
from domains.ingredient.models import Ingredient


class IngredientService:
    def __init__(self, user: User, ingredient_repo: IngredientRepository):
        self.user = user
        self.ingredient_repo = ingredient_repo

    async def add_ingredient(
        self, request: AddIngredientRequest
    ) -> List[AddIngredientResponse]:
        created_ingredients = []

        for name in request.ingredients:
            ingredient = Ingredient(
                user_id=self.user.id,
                ingredient_name=name,
                purchase_date=request.purchase_date,
            )

            saved_ingredient = await self.ingredient_repo.add_ingredient(ingredient)
            created_ingredients.append(saved_ingredient)

        return [AddIngredientResponse.model_validate(i) for i in created_ingredients]
