from sqlalchemy import select
from sqlalchemy.sql import Select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio.session import AsyncSession
from typing import Optional, Any

from core.exception.exceptions import DatabaseException, UnexpectedException
from domains.user.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_user(self, user: User):
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def _get_user_by_field(self, field_name: str, value: Any) -> Optional[User]:
        try:
            field = getattr(User, field_name)
            stmt: Select = select(User).where(field == value)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"DB 조회 오류: {str(e)}")
        except Exception as e:
            raise UnexpectedException(detail=f"예기치 못한 에러: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self._get_user_by_field("email", email)

    async def get_user_by_nickname(self, nickname: str) -> Optional[User]:
        return await self._get_user_by_field("nickname", nickname)

    async def get_user_by_phone_num(self, phone_hash: str) -> Optional[User]:
        return await self._get_user_by_field("phone_hash", phone_hash)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        return await self._get_user_by_field("id", user_id)
