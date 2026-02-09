from fastapi import Request
from redis.asyncio import Redis
import httpx
import secrets

from core import security
from core.config import settings

from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    InvalidCheckedPasswordException,
    DuplicatePhoneNumException,
    InvalidCredentialsException,
    UserNotFoundException,
    TokenExpiredException,
    TokenForbiddenException,
    PasswordUnchangedException,
    PasswordMismatchException,
    IncorrectPasswordException,
)
from domains.user.repository import UserRepository
from domains.user.schemas import (
    SignUpRequest,
    LogInRequest,
    LogInResponse,
    InfoResponse,
    RefreshTokenRequest,
    LogOutRequest,
    FindEmailRequest,
    FindEmailResponse,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ChangeNicknameRequest,
)
from domains.user.models import User


class UserService:
    def __init__(self, user_repo: UserRepository, redis: Redis):
        self.user_repo = user_repo
        self.redis = redis

    async def get_user_by_token(self, access_token: str, req: Request) -> User:
        user_id: str = security.decode_jwt(access_token=access_token)
        user: User | None = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()
        return user

    async def sign_up(self, request: SignUpRequest):
        try:
            if await self.user_repo.get_user_by_email(request.email):
                raise DuplicateEmailException()

            if await self.user_repo.get_user_by_nickname(request.nickname):
                raise DuplicateNicknameException()

            if request.password != request.checked_password:
                raise InvalidCheckedPasswordException()

            # 전화번호 처리 로직
            phone_hash = None
            encrypted_phone = None

            if request.phone_num:
                phone_hash = security.make_phone_hash(request.phone_num)

                if await self.user_repo.get_user_by_phone_num(phone_hash):
                    raise DuplicatePhoneNumException()

                encrypted_phone = security.encrypt_phone(request.phone_num)

            hashed_password = security.hash_password(request.password)

            user = User(
                email=request.email,
                password=hashed_password,
                nickname=request.nickname,
                name=request.name,
                birth=request.birth,
                phone=encrypted_phone,
                phone_hash=phone_hash,
            )
            saved_user = await self.user_repo.save_user(user)
            return saved_user

        except Exception as e:
            raise e

    async def log_in(self, request: LogInRequest, req: Request):
        try:
            user = await self.user_repo.get_user_by_email(email=request.email)

            if not user or not security.verify_password(request.password, user.password):
                raise InvalidCredentialsException()

            user_id = str(user.id)

            access_token = security.create_jwt(user_id=user.id)
            refresh_token = security.create_refresh_token()
            await self.redis.set(
                name=f"RT:{refresh_token}",
                value=user_id,
                ex=60 * 60 * 24 * 14,  # 14일 뒤 자동 삭제
            )

            return LogInResponse(
                access_token=access_token,
                refresh_token=refresh_token,
            )

        except InvalidCredentialsException:
            raise

        except Exception as e:
            raise e

    async def get_user_info(self, user_id: str) -> InfoResponse:
        user = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        return InfoResponse(email=user.email, nickname=user.nickname)

    async def refresh_token(self, request: RefreshTokenRequest) -> LogInResponse:
        redis_key = f"RT:{request.refresh_token}"
        user_id = await self.redis.get(redis_key)

        if not user_id:
            raise TokenExpiredException()

        new_access_token = security.create_jwt(user_id=user_id)

        return LogInResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,
        )

    async def log_out(self, request: LogOutRequest, user_id: str) -> None:
        redis_key = f"RT:{request.refresh_token}"

        stored_user_id = await self.redis.get(redis_key)

        if not stored_user_id:
            raise TokenExpiredException()

        if stored_user_id != str(user_id):
            raise TokenForbiddenException()

        await self.redis.delete(redis_key)

        return None

    async def find_email(self, request: FindEmailRequest) -> FindEmailResponse:
        phone_hash = security.make_phone_hash(request.phone_num)

        user = await self.user_repo.find_user_by_recovery_info(
            name=request.name, birth=request.birth, phone_hash=phone_hash
        )

        if not user:
            raise UserNotFoundException()

        return FindEmailResponse(email=user.email)

    async def change_password(self, request: ChangePasswordRequest, user_id: str) -> None:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        if not security.verify_password(request.current_password, user.password):
            raise IncorrectPasswordException()

        if security.verify_password(request.new_password, user.password):
            raise PasswordUnchangedException()

        if request.new_password != request.checked_new_password:
            raise PasswordMismatchException()

        user.password = security.hash_password(request.new_password)
        await self.user_repo.update_user(user)

    async def reset_password(self, request: ResetPasswordRequest) -> None:
        if request.new_password != request.checked_new_password:
            raise PasswordMismatchException()

        phone_hash = security.make_phone_hash(request.phone_num)
        user = await self.user_repo.get_user_by_email(request.email)

        if not user or user.name != request.name or user.birth != request.birth or user.phone_hash != phone_hash:
            raise UserNotFoundException()

        if security.verify_password(request.new_password, user.password):
            raise PasswordUnchangedException()

        user.password = security.hash_password(request.new_password)
        await self.user_repo.update_user(user)

    async def change_nickname(self, request: ChangeNicknameRequest, user_id: str) -> None:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        if user.nickname == request.nickname:
            raise DuplicateNicknameException(detail="현재 닉네임과 동일합니다.")

        existing_user = await self.user_repo.get_user_by_nickname(request.nickname)

        if existing_user:
            raise DuplicateNicknameException(detail="이미 사용 중인 닉네임입니다.")

        user.nickname = request.nickname
        await self.user_repo.update_user(user)


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
        # 0. State 검증
        redis_key = f"OAUTH_STATE:{state}"
        saved_state = await self.redis.get(redis_key)

        if not saved_state:
            raise InvalidCredentialsException(detail="유효하지 않은 접근입니다. (State 불일치)")

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
