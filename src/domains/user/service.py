from core import security

from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    InvalidCheckedPasswordException,
    DuplicatePhoneNumException,
    UserNotFoundException,
    PasswordUnchangedException,
    PasswordMismatchException,
    IncorrectPasswordException,
)
from domains.user.repository import UserRepository
from domains.user.schemas import (
    SignUpRequest,
    InfoResponse,
    FindEmailRequest,
    FindEmailResponse,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ChangeNicknameRequest,
)
from domains.user.models import User


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

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

    async def get_user_info(self, user_id: str) -> InfoResponse:
        user = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        return InfoResponse(email=user.email, nickname=user.nickname)

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
