from dataclasses import dataclass
from datetime import date
from uuid import UUID

from core import security
from core.exception.codes import ErrorCode
from core.exception.exceptions import (
    BadRequestException,
    ConflictException,
    InvalidTokenException,
    UnAuthorizedException,
    UserNotFoundException,
)
from domains.auth import kakao_client
from domains.auth.email_service import EmailService
from domains.auth.refresh_store import RefreshTokenStore
from domains.auth.schemas import (
    EmailResendRequest,
    EmailVerifyRequest,
    KakaoAuthResponse,
    KakaoCompleteRequest,
    KakaoNeedsProfileResponse,
    LogInRequest,
    LogInResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SignupAcceptedResponse,
    SignUpRequest,
)
from domains.auth.signup_pending_store import PendingSignup, SignupPendingStore
from domains.auth.verification_store import (
    CODE_TTL_SECONDS,
    PURPOSE_PASSWORD_RESET,
    PURPOSE_SIGNUP,
    VerificationCodeStore,
)
from domains.user.model import User
from domains.user.repository import UserRepository
from domains.user.schemas import UserInfoResponse

KAKAO_PROVIDER = "kakao"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    """사용자 인증관련 서비스"""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_store: RefreshTokenStore,
        verification_store: VerificationCodeStore,
        email_service: EmailService,
        signup_pending_store: SignupPendingStore,
    ) -> None:
        self.user_repo = user_repo
        self.refresh_store = refresh_store
        self.verification_store = verification_store
        self.email_service = email_service
        self.signup_pending_store = signup_pending_store

    async def issue_tokens(self, user: User) -> TokenPair:
        """
        Access Token과 Refresh Token을 쌍으로 발급하여 반환
        """
        access_token = security.create_jwt(user.id)
        refresh_token = security.create_refresh_token()
        await self.refresh_store.save(refresh_token, user.id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def _to_auth_response(self, user: User, tokens: TokenPair) -> LogInResponse:
        """
        로그인 및 refresh 이후 반환될 값 재사용
        """
        return LogInResponse(
            info=UserInfoResponse.from_user(user),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )

    def _to_kakao_auth_response(self, user: User, tokens: TokenPair) -> KakaoAuthResponse:
        return KakaoAuthResponse(
            info=UserInfoResponse.from_user(user),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )

    async def log_in(self, request: LogInRequest) -> LogInResponse:
        """
        이메일/비밀번호 로그인 처리 및 토큰(Access, Refresh) 발급
        """

        # 1. 사용자 확인 및 비밀번호 검증
        user = await self.user_repo.get_user_by_email(str(request.email))

        if not user:
            raise UnAuthorizedException(detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        if user.password is None:
            raise UnAuthorizedException(detail="카카오로 로그인해 주세요.")
        if not security.verify_password(request.password, user.password):
            raise UnAuthorizedException(detail="이메일 또는 비밀번호가 올바르지 않습니다.")

        # 2. 토큰 생성(Access, Refresh)
        tokens = await self.issue_tokens(user)
        return self._to_auth_response(user, tokens)

    async def signup(self, request: SignUpRequest) -> SignupAcceptedResponse:
        """
        회원가입 요청: 중복 검증 후 DB에 바로 쓰지 않고 Redis에 임시 저장,
        이메일 인증 코드를 발송함. 실제 계정 생성은 verify_email에서 이루어짐
        """
        email = str(request.email)
        if await self.user_repo.get_user_by_email(email):
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

        phone_hash = security.make_phone_hash(request.phone_num)
        if await self.user_repo.get_user_by_phone_num(phone_hash):
            raise ConflictException(code=ErrorCode.PHONE_NUM_CONFLICT, detail="이미 사용 중인 전화번호 입니다.")

        pending = PendingSignup(
            email=email,
            password_hash=security.hash_password(request.password),
            nickname=request.nickname,
            name=request.name,
            birth=request.birth.isoformat(),
            phone=security.encrypt_phone(request.phone_num),
            phone_hash=phone_hash,
        )
        await self.signup_pending_store.upsert(pending)

        code = await self.verification_store.issue(PURPOSE_SIGNUP, email)
        await self.email_service.send_verification_code(email, code, PURPOSE_SIGNUP)
        return SignupAcceptedResponse(
            email=email,
            message="인증 코드를 이메일로 발송했습니다.",
            expires_in_seconds=CODE_TTL_SECONDS,
        )

    async def verify_email(self, request: EmailVerifyRequest) -> LogInResponse:
        """
        회원가입 이메일 인증 완료: 코드 검증 성공 시 대기 중이던 가입 정보로
        실제 User row를 생성하고 로그인 토큰을 발급함
        """
        email = str(request.email)
        await self.verification_store.verify(PURPOSE_SIGNUP, email, request.code)

        pending = await self.signup_pending_store.pop(email)
        if pending is None:
            raise UserNotFoundException(detail="회원가입 정보가 만료되었습니다. 다시 가입해주세요.")

        user = User(
            email=pending.email,
            password=pending.password_hash,
            nickname=pending.nickname,
            name=pending.name,
            birth=date.fromisoformat(pending.birth),
            phone=pending.phone,
            phone_hash=pending.phone_hash,
        )
        user = await self.user_repo.save_user(user)
        tokens = await self.issue_tokens(user)
        return self._to_auth_response(user, tokens)

    async def resend_verification(self, request: EmailResendRequest) -> SignupAcceptedResponse:
        email = str(request.email)
        pending = await self.signup_pending_store.get(email)
        if pending is None:
            raise UserNotFoundException(detail="회원가입 요청 정보를 찾을 수 없습니다.")

        code = await self.verification_store.resend(PURPOSE_SIGNUP, email)
        await self.email_service.send_verification_code(email, code, PURPOSE_SIGNUP)
        return SignupAcceptedResponse(
            email=email,
            message="인증 코드를 재발송했습니다.",
            expires_in_seconds=CODE_TTL_SECONDS,
        )

    async def request_password_reset(self, request: PasswordResetRequest) -> dict[str, str]:
        """
        비밀번호 재설정 코드 발송: 이메일 존재 여부와 무관하게
        항상 같은 응답을 반환함(이메일 열거 공격 방지)
        """
        email = str(request.email)
        user = await self.user_repo.get_user_by_email(email)
        if user is not None and user.password is not None:
            code = await self.verification_store.issue(PURPOSE_PASSWORD_RESET, email)
            await self.email_service.send_verification_code(email, code, PURPOSE_PASSWORD_RESET)
        return {"message": "비밀번호 재설정 인증 코드를 이메일로 발송했습니다."}

    async def confirm_password_reset(self, request: PasswordResetConfirmRequest) -> dict[str, str]:
        email = str(request.email)
        user = await self.user_repo.get_user_by_email(email)
        if user is None or user.password is None:
            raise BadRequestException(
                code=ErrorCode.INVALID_VERIFICATION_CODE,
                detail="인증 코드가 올바르지 않거나 만료되었습니다.",
            )

        await self.verification_store.verify(PURPOSE_PASSWORD_RESET, email, request.code)

        user.password = security.hash_password(request.new_password)
        await self.user_repo.save_user(user)
        await self.refresh_store.revoke_all_for_user(user.id)
        return {"message": "비밀번호가 재설정되었습니다."}

    async def login_with_kakao(self, access_token: str) -> KakaoAuthResponse | KakaoNeedsProfileResponse:
        kakao_id = await kakao_client.fetch_kakao_user_id(access_token)
        user = await self.user_repo.get_user_by_social_id(KAKAO_PROVIDER, kakao_id)
        if user:
            tokens = await self.issue_tokens(user)
            return self._to_kakao_auth_response(user, tokens)
        signup_token = security.create_kakao_signup_token(kakao_id)
        return KakaoNeedsProfileResponse(signup_token=signup_token)

    async def complete_kakao_signup(self, request: KakaoCompleteRequest) -> KakaoAuthResponse:
        kakao_id = security.decode_kakao_signup_token(request.signup_token)

        existing = await self.user_repo.get_user_by_social_id(KAKAO_PROVIDER, kakao_id)
        if existing:
            tokens = await self.issue_tokens(existing)
            return self._to_kakao_auth_response(existing, tokens)

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

        phone_hash = security.make_phone_hash(request.phone_num)
        if await self.user_repo.get_user_by_phone_num(phone_hash):
            raise ConflictException(code=ErrorCode.PHONE_NUM_CONFLICT, detail="이미 사용 중인 전화번호 입니다.")

        user = User(
            email=str(request.email),
            password=None,
            provider=KAKAO_PROVIDER,
            social_id=kakao_id,
            nickname=request.nickname,
            name=request.name,
            birth=request.birth,
            phone=security.encrypt_phone(request.phone_num),
            phone_hash=phone_hash,
        )
        user = await self.user_repo.save_user(user)
        tokens = await self.issue_tokens(user)
        return self._to_kakao_auth_response(user, tokens)

    async def refresh(self, refresh_token: str) -> LogInResponse:
        user_id = await self.refresh_store.pop_user_id(refresh_token)
        if user_id is None:
            raise InvalidTokenException(detail="유효하지 않은 리프레시 토큰입니다.")
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise InvalidTokenException(detail="유효하지 않은 리프레시 토큰입니다.")
        tokens = await self.issue_tokens(user)
        return self._to_auth_response(user, tokens)

    async def log_out(self, refresh_token: str) -> None:
        await self.refresh_store.delete(refresh_token)

    async def get_user_by_token(self, access_token: str) -> User:
        user_id = UUID(security.decode_jwt(access_token))
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UnAuthorizedException(detail="사용자를 찾을 수 없습니다.")
        return user
