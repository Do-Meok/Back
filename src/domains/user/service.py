from uuid import UUID

from core import security
from core.exception.codes import ErrorCode
from core.exception.exceptions import BadRequestException, ConflictException, UserNotFoundException
from domains.auth.refresh_store import RefreshTokenStore
from domains.user.model import User
from domains.user.repository import UserRepository
from domains.user.schemas import SignUpRequest, UserInfoResponse


class UserService:
    def __init__(
            self,
            user_repo: UserRepository,
            refresh_store: RefreshTokenStore | None = None,
    ):
        self.user_repo = user_repo
        self.refresh_store = refresh_store

    async def sign_up(self, request: SignUpRequest) -> User:
        # 1. 중복 및 유효성 검증
        if await self.user_repo.get_user_by_email(str(request.email)):
            raise ConflictException(
                code=ErrorCode.EMAIL_CONFLICT,
                detail="이미 사용 중인 이메일 입니다.",
            )
        if await self.user_repo.get_user_by_nickname(request.nickname):
            raise ConflictException(
                code=ErrorCode.NICKNAME_CONFLICT,
                detail="이미 사용 중인 닉네임 입니다.(대소문자 구별)",
            )

        if request.password != request.checked_password:
            raise BadRequestException(
                code=ErrorCode.PASSWORD_MISMATCH,
                detail="비밀번호와 비밀번호 확인이 일치하지 않습니다.",
            )
        # 2. 데이터 보안 처리(전화번호 -> 암호화 + 해시화, 비밀번호 -> 해시화)
        phone_hash = None
        encrypted_phone = None

        if request.phone_num:
            phone_hash = security.make_phone_hash(request.phone_num)

            if await self.user_repo.get_user_by_phone_num(phone_hash):
                raise ConflictException(
                    code=ErrorCode.PHONE_NUM_CONFLICT,
                    detail="이미 사용 중인 전화번호 입니다."
                )

            encrypted_phone = security.encrypt_phone(request.phone_num)

        hashed_password = security.hash_password(request.password)

        # 3. 유저 생성 및 저장
        user = User(
            email=str(request.email),
            password=hashed_password,
            nickname=request.nickname,
            name=request.name,
            birth=request.birth,
            phone=encrypted_phone,
            phone_hash=phone_hash,
        )

        return await self.user_repo.save_user(user)

    async def get_user_info(self, user_id: UUID) -> UserInfoResponse:
        """
        특정 유저의 프로필 정보를 조회
        암호화된 전화번호는 복호화하여 반환함
        """
        user = await self.user_repo.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException()

        decrypted_phone = security.decrypt_phone(user.phone) if user.phone else None

        return UserInfoResponse.from_user(user, phone_num=decrypted_phone)
'''

    async def find_email(self, request: FindEmailRequest) -> FindEmailResponse:
        """본인 인증 정보를 바탕으로 가입된 이메일을 찾음"""
        phone_hash = security.make_phone_hash(request.phone_num)

        user = await self.user_repo.find_user_by_recovery_info(
            name=request.name, birth=request.birth, phone_hash=phone_hash
        )

        if not user:
            raise UserNotFoundException()

        return FindEmailResponse(email=user.email)

    async def change_password(self, request: ChangePasswordRequest, user_id: str) -> None:
        """로그인 상태에서 기존 비밀번호 확인후 새 비밀번호로 변경"""
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        # 기존 비밀번호 일치 여부 확인
        if not security.verify_password(request.current_password, user.password):
            raise IncorrectPasswordException()

        # 새 비밀번호가 기존과 동일한지 확인
        if security.verify_password(request.new_password, user.password):
            raise PasswordUnchangedException()

        # 새 비밀번호와 확인한 비밀번호 동일한지 확인
        if request.new_password != request.checked_new_password:
            raise PasswordMismatchException()

        # 새 비밀번호 해시화해서 저장
        user.password = security.hash_password(request.new_password)
        await self.user_repo.save_user(user)

    async def reset_password(self, request: ResetPasswordRequest) -> None:
        """비밀번호 분실 시 인증 정보를 확인하여 비밀번호를 재설정"""
        user = await self.user_repo.get_user_by_email(request.email)
        phone_hash = security.make_phone_hash(request.phone_num)

        # 정보 일치 여부 통합 검증
        if not user or any([user.name != request.name, user.birth != request.birth, user.phone_hash != phone_hash]):
            raise UserNotFoundException()

        # 새 비밀번호와 확인한 비밀번호 동일한지 확인
        if request.new_password != request.checked_new_password:
            raise PasswordMismatchException()

        # 새 비밀번호가 기존과 동일한지 확인
        if security.verify_password(request.new_password, user.password):
            raise PasswordUnchangedException()

        # 변경할 비밀번호 해시화해서 저
        user.password = security.hash_password(request.new_password)
        await self.user_repo.save_user(user)

    async def change_nickname(self, request: ChangeNicknameRequest, user_id: str) -> None:
        """사용자의 닉네임을 변경, 중복 닉네임 로직 포함"""

        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException()

        if user.nickname == request.nickname:
            raise DuplicateNicknameException(detail="현재 닉네임과 동일합니다.")

        if await self.user_repo.get_user_by_nickname(request.nickname):
            raise DuplicateNicknameException(detail="이미 사용 중인 닉네임입니다.")

        user.nickname = request.nickname
        await self.user_repo.save_user(user)
'''