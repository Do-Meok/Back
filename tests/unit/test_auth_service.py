from datetime import date
from unittest.mock import AsyncMock

import pytest
import uuid6

from core import security
from core.exception.exceptions import (
    BadRequestException,
    ConflictException,
    InvalidTokenException,
    UnAuthorizedException,
    UserNotFoundException,
)
from core.quota import QuotaInfo
from domains.auth.schemas import (
    EmailResendRequest,
    EmailVerifyRequest,
    LogInRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SignUpRequest,
)
from domains.auth.service import AuthService
from domains.auth.signup_pending_store import PendingSignup
from domains.user.model import User


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def refresh_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def verification_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def email_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def signup_pending_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def daily_quota_store() -> AsyncMock:
    store = AsyncMock()
    store.consume.return_value = QuotaInfo(limit=5, used=1, remaining=4)
    store.get_remaining.return_value = QuotaInfo(limit=5, used=0, remaining=5)
    return store


@pytest.fixture
def auth_service(
    user_repo: AsyncMock,
    refresh_store: AsyncMock,
    verification_store: AsyncMock,
    email_service: AsyncMock,
    signup_pending_store: AsyncMock,
    daily_quota_store: AsyncMock,
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        refresh_store=refresh_store,
        verification_store=verification_store,
        email_service=email_service,
        signup_pending_store=signup_pending_store,
        daily_quota_store=daily_quota_store,
    )


@pytest.fixture
def signup_request() -> SignUpRequest:
    return SignUpRequest(
        email="new@example.com",
        password="password123",
        checked_password="password123",
        nickname="newbie",
        name="테스트유저",
        birth=date(1990, 1, 1),
        phone_num="010-1234-5678",
    )


@pytest.fixture
def existing_user() -> User:
    return User(
        id=uuid6.uuid7(),
        email="test@example.com",
        password=security.hash_password("password123"),
        nickname="testuser",
        name="테스트유저",
        birth=date(1990, 1, 1),
    )


async def test_login_returns_access_and_refresh(
    auth_service: AuthService,
    user_repo: AsyncMock,
    refresh_store: AsyncMock,
    existing_user: User,
):
    user_repo.get_user_by_email.return_value = existing_user

    response = await auth_service.log_in(LogInRequest(email="test@example.com", password="password123"))

    assert response.access_token
    assert response.refresh_token
    assert response.info.email == "test@example.com"
    refresh_store.save.assert_awaited_once()


async def test_login_raises_when_user_not_found(auth_service: AuthService, user_repo: AsyncMock):
    user_repo.get_user_by_email.return_value = None

    with pytest.raises(UnAuthorizedException):
        await auth_service.log_in(LogInRequest(email="missing@example.com", password="password123"))


async def test_login_raises_on_wrong_password(auth_service: AuthService, user_repo: AsyncMock, existing_user: User):
    user_repo.get_user_by_email.return_value = existing_user

    with pytest.raises(UnAuthorizedException):
        await auth_service.log_in(LogInRequest(email="test@example.com", password="wrong-password"))


async def test_login_rejects_kakao_only_user(auth_service: AuthService, user_repo: AsyncMock):
    kakao_user = User(
        id=uuid6.uuid7(),
        email="kakao@example.com",
        password=None,
        social_id="1234567890",
        nickname="kakaouser",
    )
    user_repo.get_user_by_email.return_value = kakao_user

    with pytest.raises(UnAuthorizedException, match="카카오로 로그인해 주세요"):
        await auth_service.log_in(LogInRequest(email="kakao@example.com", password="password123"))


async def test_login_with_kakao_returns_tokens_for_existing_user(
    auth_service: AuthService,
    user_repo: AsyncMock,
    refresh_store: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
):
    kakao_user = User(
        id=uuid6.uuid7(),
        email="kakao@example.com",
        password=None,
        social_id="1234567890",
        nickname="kakaouser",
        name="테스트유저",
        birth=date(1990, 1, 1),
    )
    user_repo.get_user_by_social_id.return_value = kakao_user

    async def fake_fetch(_token: str) -> str:
        return "1234567890"

    monkeypatch.setattr("domains.auth.kakao_client.fetch_kakao_user_id", fake_fetch)

    response = await auth_service.login_with_kakao("kakao-access-token")

    assert response.status == "authenticated"
    assert response.info.email == "kakao@example.com"
    assert response.access_token
    assert response.refresh_token
    refresh_store.save.assert_awaited_once()


async def test_login_with_kakao_returns_needs_profile_for_new_user(
    auth_service: AuthService,
    user_repo: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
):
    user_repo.get_user_by_social_id.return_value = None

    async def fake_fetch(_token: str) -> str:
        return "999888777"

    monkeypatch.setattr("domains.auth.kakao_client.fetch_kakao_user_id", fake_fetch)

    response = await auth_service.login_with_kakao("kakao-access-token")

    assert response.status == "needs_profile"
    assert response.signup_token
    assert security.decode_kakao_signup_token(response.signup_token) == "999888777"


async def test_complete_kakao_signup_creates_user(
    auth_service: AuthService,
    user_repo: AsyncMock,
    refresh_store: AsyncMock,
):
    user_repo.get_user_by_social_id.return_value = None
    user_repo.get_user_by_email.return_value = None
    user_repo.get_user_by_nickname.return_value = None
    user_repo.get_user_by_phone_num.return_value = None

    created = User(
        id=uuid6.uuid7(),
        email="new@example.com",
        password=None,
        social_id="999888777",
        nickname="newbie",
        name="테스트유저",
        birth=date(1990, 1, 1),
    )
    user_repo.save_user.return_value = created

    signup_token = security.create_kakao_signup_token("999888777")
    from domains.auth.schemas import KakaoCompleteRequest

    response = await auth_service.complete_kakao_signup(
        KakaoCompleteRequest(
            signup_token=signup_token,
            nickname="newbie",
            email="new@example.com",
            name="테스트유저",
            birth=date(1990, 1, 1),
            phone_num="010-1234-5678",
        )
    )

    assert response.status == "authenticated"
    assert response.info.nickname == "newbie"
    user_repo.save_user.assert_awaited_once()
    refresh_store.save.assert_awaited_once()


async def test_complete_kakao_signup_rejects_email_conflict(auth_service: AuthService, user_repo: AsyncMock):
    from core.exception.exceptions import ConflictException
    from domains.auth.schemas import KakaoCompleteRequest

    user_repo.get_user_by_social_id.return_value = None
    user_repo.get_user_by_email.return_value = User(
        id=uuid6.uuid7(),
        email="taken@example.com",
        password=security.hash_password("password123"),
        nickname="other",
    )

    signup_token = security.create_kakao_signup_token("999888777")

    with pytest.raises(ConflictException):
        await auth_service.complete_kakao_signup(
            KakaoCompleteRequest(
                signup_token=signup_token,
                nickname="newbie",
                email="taken@example.com",
                name="테스트유저",
                birth=date(1990, 1, 1),
                phone_num="010-1234-5678",
            )
        )


async def test_refresh_rotates_tokens(
    auth_service: AuthService,
    user_repo: AsyncMock,
    refresh_store: AsyncMock,
    existing_user: User,
):
    refresh_store.pop_user_id.return_value = existing_user.id
    user_repo.get_user_by_id.return_value = existing_user

    old = "old-refresh"
    response = await auth_service.refresh(old)

    assert response.access_token
    assert response.refresh_token
    assert response.refresh_token != old
    assert response.info.email == existing_user.email
    refresh_store.save.assert_awaited_once()


async def test_refresh_rejects_unknown_token(auth_service: AuthService, refresh_store: AsyncMock):
    refresh_store.pop_user_id.return_value = None
    with pytest.raises(InvalidTokenException):
        await auth_service.refresh("missing")


async def test_logout_deletes_refresh(auth_service: AuthService, refresh_store: AsyncMock):
    await auth_service.log_out("some-refresh")
    refresh_store.delete.assert_awaited_once_with("some-refresh")


async def test_get_user_by_token_returns_user(auth_service: AuthService, user_repo: AsyncMock, existing_user: User):
    token = security.create_jwt(existing_user.id)
    user_repo.get_user_by_id.return_value = existing_user

    user = await auth_service.get_user_by_token(token)

    assert user.id == existing_user.id


async def test_get_user_by_token_raises_when_user_missing(
    auth_service: AuthService, user_repo: AsyncMock, existing_user: User
):
    token = security.create_jwt(existing_user.id)
    user_repo.get_user_by_id.return_value = None

    with pytest.raises(UnAuthorizedException):
        await auth_service.get_user_by_token(token)


# --- 회원가입 이메일 인증 ---


async def test_signup_upserts_pending_and_sends_code(
    auth_service: AuthService,
    user_repo: AsyncMock,
    verification_store: AsyncMock,
    email_service: AsyncMock,
    signup_pending_store: AsyncMock,
    daily_quota_store: AsyncMock,
    signup_request: SignUpRequest,
):
    user_repo.get_user_by_email.return_value = None
    user_repo.get_user_by_nickname.return_value = None
    user_repo.get_user_by_phone_num.return_value = None
    verification_store.issue.return_value = "123456"

    response = await auth_service.signup(signup_request)

    assert response.email == "new@example.com"
    assert response.expires_in_seconds > 0
    assert response.quota_remaining == 4
    signup_pending_store.upsert.assert_awaited_once()
    verification_store.issue.assert_awaited_once_with("signup", "new@example.com")
    email_service.send_verification_code.assert_awaited_once_with("new@example.com", "123456", "signup")
    user_repo.save_user.assert_not_awaited()
    daily_quota_store.consume.assert_awaited_once_with("email_send", "new@example.com", 5)


async def test_signup_blocked_when_quota_exceeded(
    auth_service: AuthService,
    user_repo: AsyncMock,
    daily_quota_store: AsyncMock,
    signup_pending_store: AsyncMock,
    signup_request: SignUpRequest,
):
    from core.exception.exceptions import RateLimitExceededException

    user_repo.get_user_by_email.return_value = None
    user_repo.get_user_by_nickname.return_value = None
    user_repo.get_user_by_phone_num.return_value = None
    daily_quota_store.consume.side_effect = RateLimitExceededException()

    with pytest.raises(RateLimitExceededException):
        await auth_service.signup(signup_request)

    # quota 초과 시 pending 상태를 아예 만들지 않아야 함
    signup_pending_store.upsert.assert_not_awaited()


async def test_signup_rejects_email_conflict(
    auth_service: AuthService, user_repo: AsyncMock, existing_user: User, signup_request: SignUpRequest
):
    user_repo.get_user_by_email.return_value = existing_user

    with pytest.raises(ConflictException):
        await auth_service.signup(signup_request)


async def test_signup_rejects_password_mismatch(auth_service: AuthService, user_repo: AsyncMock):
    user_repo.get_user_by_email.return_value = None
    user_repo.get_user_by_nickname.return_value = None
    request = SignUpRequest(
        email="new@example.com",
        password="password123",
        checked_password="different123",
        nickname="newbie",
        name="테스트유저",
        birth=date(1990, 1, 1),
        phone_num="010-1234-5678",
    )

    with pytest.raises(BadRequestException):
        await auth_service.signup(request)


async def test_verify_email_creates_user_and_issues_tokens(
    auth_service: AuthService,
    user_repo: AsyncMock,
    verification_store: AsyncMock,
    signup_pending_store: AsyncMock,
    refresh_store: AsyncMock,
):
    pending = PendingSignup(
        email="new@example.com",
        password_hash=security.hash_password("password123"),
        nickname="newbie",
        name="테스트유저",
        birth=date(1990, 1, 1).isoformat(),
        phone=security.encrypt_phone("010-1234-5678"),
        phone_hash=security.make_phone_hash("010-1234-5678"),
    )
    signup_pending_store.pop.return_value = pending
    created = User(
        id=uuid6.uuid7(),
        email=pending.email,
        password=pending.password_hash,
        nickname=pending.nickname,
        name=pending.name,
        birth=date(1990, 1, 1),
    )
    user_repo.save_user.return_value = created

    response = await auth_service.verify_email(EmailVerifyRequest(email="new@example.com", code="123456"))

    verification_store.verify.assert_awaited_once_with("signup", "new@example.com", "123456")
    assert response.info.email == "new@example.com"
    assert response.access_token
    refresh_store.save.assert_awaited_once()


async def test_verify_email_raises_when_pending_expired(
    auth_service: AuthService, verification_store: AsyncMock, signup_pending_store: AsyncMock
):
    signup_pending_store.pop.return_value = None

    with pytest.raises(UserNotFoundException):
        await auth_service.verify_email(EmailVerifyRequest(email="new@example.com", code="123456"))


async def test_resend_verification_requires_pending_signup(auth_service: AuthService, signup_pending_store: AsyncMock):
    signup_pending_store.get.return_value = None

    with pytest.raises(UserNotFoundException):
        await auth_service.resend_verification(EmailResendRequest(email="new@example.com"))


# --- 비밀번호 재설정 ---


async def test_request_password_reset_sends_code_for_local_user(
    auth_service: AuthService,
    user_repo: AsyncMock,
    verification_store: AsyncMock,
    email_service: AsyncMock,
    existing_user: User,
):
    user_repo.get_user_by_email.return_value = existing_user
    verification_store.issue.return_value = "654321"

    response = await auth_service.request_password_reset(PasswordResetRequest(email=existing_user.email))

    assert response.quota_remaining == 4
    verification_store.issue.assert_awaited_once_with("password_reset", existing_user.email)
    email_service.send_verification_code.assert_awaited_once()


async def test_request_password_reset_silently_ignores_unknown_email(
    auth_service: AuthService,
    user_repo: AsyncMock,
    verification_store: AsyncMock,
    email_service: AsyncMock,
    daily_quota_store: AsyncMock,
):
    user_repo.get_user_by_email.return_value = None

    response = await auth_service.request_password_reset(PasswordResetRequest(email="ghost@example.com"))

    assert response.message
    verification_store.issue.assert_not_awaited()
    email_service.send_verification_code.assert_not_awaited()
    # 존재하지 않는 이메일이어도 quota는 동일하게 소모되어야 함(존재 여부 노출 방지)
    daily_quota_store.consume.assert_awaited_once_with("email_send", "ghost@example.com", 5)


async def test_confirm_password_reset_updates_password_and_revokes_sessions(
    auth_service: AuthService,
    user_repo: AsyncMock,
    verification_store: AsyncMock,
    refresh_store: AsyncMock,
    existing_user: User,
):
    user_repo.get_user_by_email.return_value = existing_user

    await auth_service.confirm_password_reset(
        PasswordResetConfirmRequest(
            email=existing_user.email,
            code="654321",
            new_password="newpassword123",
            checked_new_password="newpassword123",
        )
    )

    verification_store.verify.assert_awaited_once_with("password_reset", existing_user.email, "654321")
    assert security.verify_password("newpassword123", existing_user.password)
    refresh_store.revoke_all_for_user.assert_awaited_once_with(existing_user.id)
