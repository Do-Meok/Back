from fastapi import Request
from redis.asyncio import Redis

from core import security
from domains.auth.schemas import LogInRequest, RefreshTokenRequest, LogOutRequest, LogInResponse
from domains.user.exceptions import (
    UserNotFoundException,
)
from domains.auth.exceptions import InvalidCredentialsException, TokenExpiredException, TokenForbiddenException
from domains.user.models import User
from domains.user.repository import UserRepository


class AuthService:
    """사용자 인증관련 서비스"""

    def __init__(self, user_repo: UserRepository, redis: Redis):
        self.user_repo = user_repo
        self.redis = redis

    async def log_in(self, request: LogInRequest, req: Request) -> LogInResponse:
        """
        이메일/비밀번호 로그인 처리 및 토큰(Access, Refresh) 발급

        Raises:
            InvalidCredentialsException: 계정 정보 불일치 시
        """
        user = await self.user_repo.get_user_by_email(email=request.email)

        if not user or not security.verify_password(request.password, user.password):
            raise InvalidCredentialsException()

        user_id = str(user.id)
        access_token = security.create_jwt(user_id=user.id)
        refresh_token = security.create_refresh_token()

        await self.redis.set(
            name=f"RT:{refresh_token}",
            value=user_id,
            ex=60 * 60 * 24 * 14,
        )

        return LogInResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, request: RefreshTokenRequest) -> LogInResponse:
        """
        Access Token 재발급 (RTR 적용: 사용된 Refresh 토큰은 즉시 폐기)

        Raises:
            TokenExpiredException: Refresh 토큰 만료 또는 없음
        """
        redis_key = f"RT:{request.refresh_token}"
        user_id = await self.redis.get(redis_key)

        if not user_id:
            raise TokenExpiredException()

        await self.redis.delete(redis_key)

        new_access_token = security.create_jwt(user_id=user_id)
        new_refresh_token = security.create_refresh_token()

        await self.redis.set(
            name=f"RT:{new_refresh_token}",
            value=user_id,
            ex=60 * 60 * 24 * 14,
        )

        return LogInResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    async def log_out(self, request: LogOutRequest, user_id: str) -> None:
        redis_key = f"RT:{request.refresh_token}"

        stored_user_id = await self.redis.get(redis_key)

        if not stored_user_id:
            raise TokenExpiredException()

        if isinstance(stored_user_id, bytes):
            stored_user_id = stored_user_id.decode("utf-8")

        if stored_user_id != str(user_id):
            raise TokenForbiddenException()

        await self.redis.delete(redis_key)

    async def get_user_by_token(self, access_token: str) -> User:
        try:
            user_id: str = security.decode_jwt(access_token=access_token)
        except Exception:
            raise TokenForbiddenException()

        user: User | None = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        return user
