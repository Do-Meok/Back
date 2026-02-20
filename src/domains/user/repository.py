from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.exception.exceptions import DatabaseException, UnexpectedException
from domains.user.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _commit_or_rollback(self, user: User, error_msg: str) -> User:
        """세션 변경사항을 반영(commit)하거나 실패 시 롤백합니다."""
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise DatabaseException(detail=f"{error_msg}: {str(e)}")

    async def _get_one(self, *where_conditions) -> User | None:
        """조건에 맞는 엔티티 조회"""
        try:
            stmt = select(User).where(*where_conditions)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseException(detail=f"DB 조회 오류: {str(e)}")
        except Exception as e:
            raise UnexpectedException(detail=f"예기치 못한 에러: {str(e)}")

    async def get_user_by_id(self, user_id: str) -> User | None:
        """고유ID 정보로 조회"""
        return await self._get_one(User.id == user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """이메일 정보로 조회"""
        return await self._get_one(User.email == email)

    async def get_user_by_nickname(self, nickname: str) -> User | None:
        """닉네임(대소문자 무시)으로 조회"""
        return await self._get_one(func.lower(User.nickname) == nickname.lower())

    async def get_user_by_phone_num(self, phone_hash: str) -> User | None:
        """해시화된 전화번호로 조회"""
        return await self._get_one(User.phone_hash == phone_hash)

    async def save_user(self, user: User) -> User:
        return await self._commit_or_rollback(user, "유저 저장 실패")

    async def update_user(self, user: User) -> None:
        await self._commit_or_rollback(user, "데이터 업데이트 실패")

    async def find_user_by_recovery_info(self, name: str, birth: str, phone_hash: str) -> User | None:
        """
        이름, 생년월일, 전화번호 해시를 조합하여 유저를 조회 (이메일 찾기 등)
        """
        stmt = select(User).where(User.name == name, User.birth == birth, User.phone_hash == phone_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_social_id(self, provider: str, social_id: str) -> User | None:
        return await self._get_one(User.provider == provider, User.social_id == social_id)
