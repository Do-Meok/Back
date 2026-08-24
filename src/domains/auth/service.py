from domains.user.exceptions import (
    UserNotFoundException,
)
from redis.asyncio import Redis

from core import security
from domains.auth.exceptions import InvalidCredentialsException, TokenExpiredException, TokenForbiddenException
from domains.auth.schemas.request import LogInRequest, LogOutRequest, RefreshTokenRequest
from domains.auth.schemas.response import LogInResponse
from domains.user.model import User
from domains.user.repository import UserRepository


class AuthService:
    """사용자 인증관련 서비스"""

    def __init__(self, user_repo: UserRepository, refresh_store: RefreshTokenStore) -> None:
        self.user_repo = user_repo
        self.redis = redis
        self.RT_PREFIX = "RT:"  # Refresh Token Prefix
        self.REFRESH_TOKEN_EXPIRATION_TIME = 60 * 60 * 24 * 14  # 14일

    async def log_in(self, request: LogInRequest) -> LogInResponse:
        """
        이메일/비밀번호 로그인 처리 및 토큰(Access, Refresh) 발급

        Args:
            request (LogInRequest): 로그인 정보 (email, password)

        Returns:
            LoginResponse: 발급된 Access & Refresh 토큰

        Raises:
            InvalidCredentialsException: 계정 정보 불일치 시
        """

        # 1. 사용자 확인 및 비밀번호 검증
        user = await self.user_repo.get_user_by_email(email=request.email)

        if not user or not security.verify_password(request.password, user.password):
            raise InvalidCredentialsException()

        # 2. 토큰 생성(Access, Refresh)
        user_id = str(user.id)
        access_token = security.create_jwt(user_id=user.id)
        refresh_token = security.create_refresh_token()

        # 3. Redis에 Refresh Token 저장
        await self.redis.set(
            name=f"{self.RT_PREFIX}{refresh_token}",
            value=user_id,
            ex=self.REFRESH_TOKEN_EXPIRATION_TIME,
        )

        return LogInResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_token(self, request: RefreshTokenRequest) -> LogInResponse:
        """
        Refresh 토큰을 사용하여 새로운 토큰 쌍 발급 (RTR 적용)

        Args:
            request: (RefreshTokenRequest): 만료되지 않은 Refresh 토큰

        Raises:
            TokenExpiredException: Refresh 토큰 만료 또는 없음
        """

        redis_key = f"RT:{request.refresh_token}"

        # 1. 기존 Refresh 토큰 검증
        user_id = await self.redis.get(redis_key)
        if not user_id:
            raise TokenExpiredException()

        # 2. 사용된 기존 토큰 즉시 폐기 (RTR)
        await self.redis.delete(redis_key)

        # 3. 새로운 토큰 쌍 발급 및 Redis 갱신
        new_access_token = security.create_jwt(user_id=user_id)
        new_refresh_token = security.create_refresh_token()

        await self.redis.set(
            name=f"RT:{new_refresh_token}",
            value=user_id,
            ex=60 * 60 * 24 * 14,
        )

        return LogInResponse(access_token=new_access_token, refresh_token=new_refresh_token)

    async def log_out(self, request: LogOutRequest, user_id: str) -> None:
        """
        사용자 로그아웃 처리 (저장된 Refresh 토큰 삭제)

        Args:
            request (LogOutRequest): 로그아웃 할 Refresh 토큰
            user_id (str): 현재 로그인된 사용자 ID

        Raises:
            TokenExpiredException: 토큰이 이미 없거나 만료된 경우
            TokenForbiddenException: 타인의 토큰으로 로그아웃을 시도할 경우
        """
        redis_key = f"RT:{request.refresh_token}"

        # 1. 토큰 존재 여부 확인
        stored_user_id = await self.redis.get(redis_key)
        if not stored_user_id:
            raise TokenExpiredException()

        # 2. 본인 여부 확인
        if isinstance(stored_user_id, bytes):
            stored_user_id = stored_user_id.decode("utf-8")

        if stored_user_id != str(user_id):
            raise TokenForbiddenException()

        # 3. 토큰 삭제
        await self.redis.delete(redis_key)

    async def get_user_by_token(self, access_token: str) -> User:
        """Access Token을 디코딩하여 실제 유저 객체 반환 (Dependency용)"""
        try:
            user_id: str = security.decode_jwt(access_token=access_token)
        except Exception:
            raise TokenForbiddenException()

        user: User | None = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        return user
