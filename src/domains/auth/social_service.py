import secrets

import httpx
from redis.asyncio import Redis

from core import security
from core.config import settings
from domains.auth.schemas import LogInResponse
from domains.auth.exceptions import InvalidCredentialsException, OAuthStateMismatchException
from domains.user.models import User
from domains.user.repository import UserRepository


class SocialAuthService:
    def __init__(self, user_repo: UserRepository, redis: Redis):
        self.user_repo = user_repo
        self.redis = redis

    async def get_kakao_auth_url(self) -> str:
        state = secrets.token_urlsafe(32)
        await self.redis.set(f"OAUTH_STATE:{state}", "valid", ex=300)

        return (
            f"https://kauth.kakao.com/oauth/authorize?"
            f"client_id={settings.KAKAO_REST_API_KEY}&"
            f"redirect_uri={settings.KAKAO_REDIRECT_URI}&"
            f"response_type=code&"
            f"state={state}"
        )

    async def kakao_login(self, code: str, state: str) -> LogInResponse:
        redis_key = f"OAUTH_STATE:{state}"
        saved_state = await self.redis.get(redis_key)

        if not saved_state:
            raise OAuthStateMismatchException(detail="유효하지 않은 접근입니다. (State 불일치)")

        await self.redis.delete(redis_key)

        kakao_token = await self._get_kakao_token(code)

        kakao_user_info = await self._get_kakao_user_info(kakao_token)

        social_id = str(kakao_user_info["id"])

        user = await self.user_repo.get_user_by_social_id(provider="kakao", social_id=social_id)

        if not user:
            kakao_account = kakao_user_info.get("kakao_account", {})
            profile = kakao_account.get("profile", {})

            nickname = f"k_{social_id}"
            email = kakao_account.get("email")

            new_user = User(
                email=email,
                nickname=nickname,
                password=None,
                name=profile.get("nickname", "Unknown"),
                provider="kakao",
                social_id=social_id,
                phone=None,
                phone_hash=None,
            )
            user = await self.user_repo.save_user(new_user)

        return await self._issue_tokens(user)

    async def _get_kakao_token(self, code: str) -> str:
        url = "https://kauth.kakao.com/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
            "client_secret": settings.KAKAO_CLIENT_SECRET.get_secret_value(),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)

            if response.status_code != 200:
                raise InvalidCredentialsException(detail="카카오 토큰 발급 실패")

            return response.json().get("access_token")

    async def _get_kakao_user_info(self, access_token: str) -> dict:
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
        user_id = str(user.id)
        access_token = security.create_jwt(user_id=user_id)
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
