from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.exception.exceptions import DatabaseException, UnexpectedException
from domains.user.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_user(self, user: User) -> User:
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"유저 저장 실패: {str(e)}")

    async def _get_one(self, *where_conditions) -> User | None:
        try:
            stmt = select(User).where(*where_conditions)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"DB 조회 오류: {str(e)}")
        except Exception as e:
            raise UnexpectedException(detail=f"예기치 못한 에러: {str(e)}")

    async def get_user_by_email(self, email: str) -> User | None:
        return await self._get_one(User.email == email)

    async def get_user_by_nickname(self, nickname: str) -> User | None:
        return await self._get_one(User.nickname == nickname)

    async def get_user_by_phone_num(self, phone_hash: str) -> User | None:
        return await self._get_one(User.phone_hash == phone_hash)

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self._get_one(User.id == user_id)

    async def find_user_by_recovery_info(self, name: str, birth: str, phone_hash: str) -> User | None:
        stmt = select(User).where(User.name == name, User.birth == birth, User.phone_hash == phone_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(self, user: User) -> None:
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"데이터 업데이트 실패: {str(e)}")

    async def get_user_by_social_id(self, provider: str, social_id: str) -> User | None:
        return await self._get_one(User.provider == provider, User.social_id == social_id)
