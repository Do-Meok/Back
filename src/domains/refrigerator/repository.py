from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exception.exceptions import DatabaseException
from domains.refrigerator.models import Refrigerator


class RefrigeratorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_refrigerator(self, refrigerator: Refrigerator) -> Refrigerator:
        try:
            self.session.add(refrigerator)
            await self.session.commit()

            return refrigerator

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"냉장고 저장 중 오류 발생: {str(e)}")

    async def get_refrigerators(self, user_id: int) -> list[Refrigerator]:
        """특정 사용자의 모든 냉장고 목록 조회"""
        try:
            stmt = (
                select(Refrigerator)
                .options(selectinload(Refrigerator.compartments))
                .where(Refrigerator.user_id == user_id)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"냉장고 목록 조회 중 오류 발생: {str(e)}")

    async def get_refrigerator(self, refrigerator_id: int) -> Refrigerator | None:
        try:
            stmt = (
                select(Refrigerator)
                .options(selectinload(Refrigerator.compartments))
                .where(Refrigerator.id == refrigerator_id)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"냉장고 조회 중 오류 발생: {str(e)}")

    async def delete_refrigerator(self, refrigerator: Refrigerator) -> None:
        """냉장고 삭제"""
        try:
            await self.session.delete(refrigerator)
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"냉장고 삭제 중 오류 발생: {str(e)}")
