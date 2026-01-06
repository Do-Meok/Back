from fastapi import Request

from core import security

from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    InvalidCheckedPasswordException,
    DuplicatePhoneNumException,
    InvalidCredentialsException,
    UserNotFoundException,
)
from domains.user.repository import UserRepository
from domains.user.schemas import SignUpRequest, LogInRequest, LogInResponse
from domains.user.models import User


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

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

            access_token = security.create_jwt(user_id=user.id)
            return LogInResponse(access_token=access_token)

        except InvalidCredentialsException:
            raise

        except Exception as e:
            raise e
