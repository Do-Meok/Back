from fastapi import Request
from redis.asyncio import Redis

from core import security

from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    InvalidCheckedPasswordException,
    DuplicatePhoneNumException,
    InvalidCredentialsException,
    UserNotFoundException,
    TokenExpiredException,
    TokenForbiddenException,
)
from domains.user.repository import UserRepository
from domains.user.schemas import (
    SignUpRequest,
    LogInRequest,
    LogInResponse,
    InfoResponse,
    RefreshTokenRequest,
    LogOutRequest,
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

            if not user or not security.verify_password(
                request.password, user.password
            ):
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
