from uuid import UUID

from core import security
from core.exception.codes import ErrorCode
from core.exception.exceptions import (
    BadRequestException,
    ConflictException,
    UnAuthorizedException,
    UserNotFoundException,
)
from domains.auth.refresh_store import RefreshTokenStore
from domains.user.model import User
from domains.user.repository import UserRepository
from domains.user.schemas import UpdatePasswordRequest, UpdateUserRequest, UserInfoResponse


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_store: RefreshTokenStore | None = None,
    ):
        self.user_repo = user_repo
        self.refresh_store = refresh_store

    async def get_user_info(self, user_id: UUID) -> UserInfoResponse:
        """
        특정 유저의 프로필 정보를 조회
        암호화된 전화번호는 복호화하여 반환함
        """
        user = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        return UserInfoResponse.from_user(user)

    async def update_user(self, user: User, request: UpdateUserRequest) -> UserInfoResponse:
        if request.nickname is not None:
            # 본인의 현재 닉네임과 동일한 경우 불가
            if user.nickname == request.nickname:
                raise ConflictException(code=ErrorCode.NICKNAME_CONFLICT, detail="현재 사용 중인 닉네임과 동일합니다.")
            # 타인이 사용 중인 닉네임인지 검증
            existing = await self.user_repo.get_user_by_nickname(request.nickname)
            if existing and existing.id != user.id:
                raise ConflictException(
                    code=ErrorCode.NICKNAME_CONFLICT,
                    detail="이미 사용 중인 닉네임 입니다.(대소문자 구별)",
                )
            user.nickname = request.nickname

        await self.user_repo.save_user(user)
        return UserInfoResponse.from_user(user)

    async def update_password(self, user: User, request: UpdatePasswordRequest) -> UserInfoResponse:
        if user.password is not None:
            if request.current_password == request.new_password:
                raise BadRequestException(detail="현재 비밀번호와 변경할 비밀번호가 동일합니다.")
            if not request.current_password:
                raise BadRequestException(
                    code=ErrorCode.BAD_REQUEST,
                    detail="현재 비밀번호가 필요합니다.",
                )
            if not security.verify_password(request.current_password, user.password):
                raise UnAuthorizedException(detail="현재 비밀번호가 올바르지 않습니다.")

        user.password = security.hash_password(request.new_password)
        await self.user_repo.save_user(user)
        if self.refresh_store is not None:
            await self.refresh_store.revoke_all_for_user(user.id)
        return UserInfoResponse.from_user(user)
