from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, date

from core.exception.exceptions import DatabaseException
from domains.ingredient.models import Ingredient


class IngredientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_ingredients(self, ingredients: list[Ingredient]) -> list[Ingredient]:
        try:
            self.session.add_all(ingredients)
            await self.session.commit()

            return ingredients

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"식재료 일괄 저장 중 오류 발생: {str(e)}")

    async def set_ingredient(
        self, ingredient_id: int, user_id: str, expiration_date: date, storage_type: str
    ):
        try:
            stmt = select(Ingredient).where(
                Ingredient.id == ingredient_id, Ingredient.user_id == user_id
            )
            result = await self.session.execute(stmt)
            ingredient = result.scalar_one_or_none()

            if ingredient:
                ingredient.expiration_date = expiration_date
                ingredient.storage_type = storage_type

                await self.session.commit()
                return ingredient

            return None

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"식재료 수정 중 오류 발생: {str(e)}")

    async def get_ingredients(
        self,
        user_id: str,
        storage: str | None = None,
        is_unclassified: bool | None = None,
    ) -> list[Ingredient]:
        try:
            stmt = select(Ingredient).where(
                Ingredient.user_id == user_id,
                Ingredient.deleted_at.is_(None),
            )
            if is_unclassified:
                stmt = stmt.where(
                    Ingredient.expiration_date.is_(None),
                    Ingredient.storage_type.is_(None),
                )

            elif storage:
                stmt = stmt.where(Ingredient.storage_type == storage)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"식재료 목록 조회 실패: {str(e)}")

    async def get_ingredient(
        self, ingredient_id: int, user_id: str
    ) -> Ingredient | None:
        stmt = select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.user_id == user_id,
            Ingredient.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_ingredient(self, ingredient_id: int, user_id: str):
        try:
            stmt = (
                update(Ingredient)
                .where(
                    Ingredient.id == ingredient_id,
                    Ingredient.user_id == user_id,
                    Ingredient.deleted_at.is_(None),
                )
                .values(deleted_at=datetime.now(timezone.utc))
                .execution_options(synchronize_session=False)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()

            return result.rowcount > 0

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"식재료 삭제 중 오류 발생: {str(e)}")

    async def update_ingredient(
        self,
        ingredient_id: int,
        user_id: str,
        purchase_date: date | None,
        expiration_date: date | None,
        storage_type: str | None,
    ):
        try:
            stmt = select(Ingredient).where(
                Ingredient.id == ingredient_id, Ingredient.user_id == user_id
            )
            result = await self.session.execute(stmt)
            ingredient = result.scalar_one_or_none()

            # 수정하고 싶은 값만 보내고, 나머지는 None으로 보낼 떄, 기존 데이터 지킴
            if ingredient:
                if purchase_date is not None:
                    ingredient.purchase_date = purchase_date
                if expiration_date is not None:
                    ingredient.expiration_date = expiration_date
                if storage_type is not None:
                    ingredient.storage_type = storage_type

                await self.session.commit()
                return ingredient

            return None
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"식재료 수정 중 오류 발생: {str(e)}")

    async def get_ingredients_by_compartment(
        self, compartment_id: int
    ) -> list[Ingredient]:
        try:
            stmt = (
                select(Ingredient)
                .where(Ingredient.compartment_id == compartment_id)
                .where(Ingredient.deleted_at.is_(None))
                .order_by(Ingredient.purchase_date.asc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"식재료 조회 중 오류 발생: {str(e)}")
