from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Dict, Any

from core.exception.exceptions import DatabaseException
from domains.recipe.models import Recipe


class RecipeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_recipe(self, user_id: str, food_name: str, recipe: Dict[str, Any]):
        try:
            new_recipe = Recipe(user_id=user_id, food_name=food_name, recipe=recipe)
            self.session.add(new_recipe)
            await self.session.commit()
            return new_recipe
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"레시피 저장 실패: {str(e)}")

    async def get_recipes(self, user_id: str):
        try:
            stmt = select(Recipe).where(Recipe.user_id == user_id).order_by(Recipe.created_at.desc())
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"레시피 조회 실패: {str(e)}")
