from dataclasses import dataclass
from uuid import UUID

from core import security
from core.exception.codes import ErrorCode
from core.exception.exceptions import ConflictException, InvalidTokenException, UnAuthorizedException
from domains.auth import kakao_client
from domains.auth.refresh_store import RefreshTokenStore
from domains.auth.schemas import (
    KakaoAuthResponse,
    KakaoCompleteRequest,
    KakaoNeedsProfileResponse,
    LogInRequest,
    LogInResponse,
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

    def __init__(self, user_repo: UserRepository, refresh_store: RefreshTokenStore) -> None:
        self.user_repo = user_repo
        self.refresh_store = refresh_store

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
