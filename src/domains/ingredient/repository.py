from sqlalchemy.ext.asyncio import AsyncSession

from domains.ingredient.models import Ingredient


class IngredientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_ingredient(self, ingredient: Ingredient) -> Ingredient:
        self.session.add(ingredient)
        await self.session.commit()
        await self.session.refresh(ingredient)
        return ingredient
