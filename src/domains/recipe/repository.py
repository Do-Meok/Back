from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.exceptions import DatabaseException
from domains.recipe.models import Recipe


class RecipeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_recipe(self, user_id: str, food_name: str, recipe: dict[str, Any]):
        try:
            new_recipe = Recipe(user_id=user_id, food_name=food_name, recipe=recipe)
            self.session.add(new_recipe)
            await self.session.commit()
            return new_recipe
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"레시피 저장 실패: {e!s}")

    async def get_recipes(self, user_id: str):
        try:
            stmt = select(Recipe).where(Recipe.user_id == user_id).order_by(Recipe.created_at.desc())
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"레시피 조회 실패: {e!s}")

    async def get_recipe_by_id(self, recipe_id: int):
        stmt = select(Recipe).where(Recipe.id == recipe_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_recipe(self, recipe: Recipe) -> None:
        try:
            await self.session.delete(recipe)
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"레시피 삭제 중 오류 발생: {e!s}")
