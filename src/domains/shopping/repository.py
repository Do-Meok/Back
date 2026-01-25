from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.exceptions import DatabaseException
from domains.shopping.models import Shopping


class ShoppingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_item(self, shopping_item: Shopping) -> Shopping:
        try:
            self.session.add(shopping_item)
            await self.session.commit()

            return shopping_item

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"장보기 일괄 저장 중 오류 발생: {str(e)}")

    async def get_items(self, user_id: int) -> list[Shopping]:
        try:
            stmt = (
                select(Shopping)
                .where(Shopping.user_id == user_id)
                .order_by(Shopping.created_at.desc())
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()

        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"장보기 목록 조회 실패: {str(e)}")

    async def delete_item(self, shopping_id: int, user_id: str):
        try:
            stmt = (
                delete(Shopping)
                .where(
                    Shopping.id == shopping_id,
                    Shopping.user_id == user_id
                )
            )
            result = await self.session.execute(stmt)

            await self.session.commit()

            return result.rowcount > 0

        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"장보기 삭제 실패: {str(e)}")