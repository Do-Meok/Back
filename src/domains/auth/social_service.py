import secrets

import httpx
from redis.asyncio import Redis

from core import security
from core.config import settings
from domains.auth.schemas.response import LogInResponse
from domains.auth.exceptions import InvalidCredentialsException, OAuthStateMismatchException
from domains.user.models import User
from domains.user.repository import UserRepository


class SocialAuthService:
    """소셜 인증을 담당하는 서비스"""

    def __init__(self, user_repo: UserRepository, redis: Redis):
        self.user_repo = user_repo
        self.redis = redis

        # 상수 관리
        self.STATE_PREFIX = "OAUTH_STATE:"
        self.STATE_EXPIRE = 300  # 5분
        self.RT_PREFIX = "RT:"
        self.RT_EXPIRE = 60 * 60 * 24 * 14  # 14일

    async def get_kakao_auth_url(self) -> str:
        """
        카카오 로그인 페이지 URL 생성 및 CSRF 방지를 위한 state 저장
        """
        state = secrets.token_urlsafe(32)
        await self.redis.set(f"{self.STATE_PREFIX}{state}", "valid", ex=self.STATE_EXPIRE)

        params = {
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "response_type": "code",
            "state": state,
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://kauth.kakao.com/oauth/authorize?{query_string}"

    async def kakao_login(self, code: str, state: str) -> LogInResponse:
        """
        카카오 인가 코드를 통한 로그인 처리 (회원가입 포함)

        Args:
            code (str): 카카오로부터 받은 인가 코드
            state (str): CSRF 검증용 상태 값

        Returns:
            LogInResponse: 발급된 토큰 세트
        """

        # 1. State 검증 (CSRF 방지)
        redis_key = f"{self.STATE_PREFIX}{state}"
        if not await self.redis.get(redis_key):
            raise OAuthStateMismatchException(detail="유효하지 않은 접근입니다. (State 불일치)")
        await self.redis.delete(redis_key)

        # 2. 카카오 API 통신 (토큰 및 유저 정보 획득)
        kakao_token = await self._get_kakao_token(code)
        kakao_user_info = await self._get_kakao_user_info(kakao_token)
        social_id = str(kakao_user_info["id"])

        # 3. 유저 연동 처리 (기존 유저 조회 또는 신규 생성)
        user = await self.user_repo.get_user_by_social_id(provider="kakao", social_id=social_id)

        if not user:
            user = await self._register_social_user(social_id, kakao_user_info)

        # 4. 서비스 토큰 발급
        return await self._issue_tokens(user)

    async def _register_social_user(self, social_id: str, kakao_info: dict) -> User:
        """카카오 정보를 바탕으로 신규 소셜 유저 등록"""
        kakao_account = kakao_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})

        new_user = User(
            email=kakao_account.get("email"),
            nickname=f"k_{social_id}",  # 카카오 고유 ID 기반 기본 닉네임
            password=None,  # 소셜 유저는 비밀번호 없음
            name=profile.get("nickname", "Unknown"),
            provider="kakao",
            social_id=social_id,
            phone=None,
            phone_hash=None,
        )
        return await self.user_repo.save_user(new_user)

    async def _get_kakao_token(self, code: str) -> str:
        """인가 코드로 카카오 Access Token 교환"""
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
            "client_secret": settings.KAKAO_CLIENT_SECRET.get_secret_value(),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code != 200:
                raise InvalidCredentialsException(detail="카카오 토큰 발급 실패")
            return response.json().get("access_token")

    async def _get_kakao_user_info(self, access_token: str) -> dict:
        """카카오 Access Token으로 유저 프로필 조회"""
        url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise InvalidCredentialsException(detail="카카오 유저 정보 조회 실패")
            return response.json()

    async def _issue_tokens(self, user: User) -> LogInResponse:
        """서비스 자체 JWT 발급 및 Refresh Token 저장"""
        user_id = str(user.id)
        access_token = security.create_jwt(user_id=user_id)
        refresh_token = security.create_refresh_token()

        await self.redis.set(name=f"{self.RT_PREFIX}{refresh_token}", value=user_id, ex=self.RT_EXPIRE)

        return LogInResponse(access_token=access_token, refresh_token=refresh_token)
