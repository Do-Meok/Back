import pytest
from unittest.mock import AsyncMock, patch
from domains.user.service import UserService
from domains.user.schemas import (
    SignUpRequest,
    LogInRequest,
    RefreshTokenRequest,
    LogOutRequest,
)
from domains.user.exceptions import (
    DuplicateEmailException,
    InvalidCheckedPasswordException,
    InvalidCredentialsException,
    TokenExpiredException,
    TokenForbiddenException,  # [추가] 권한 없음
)
from domains.user.models import User


@pytest.mark.asyncio
class TestUserService:
    @pytest.fixture
    def mock_repo(self):
        """User Repository Mock"""
        return AsyncMock()

    @pytest.fixture
    def mock_redis(self):
        """Redis Client Mock"""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo, mock_redis):
        """UserService 인스턴스 (Mock 주입됨)"""
        return UserService(mock_repo, mock_redis)

    async def test_sign_up_success(self, service, mock_repo):
        # ✅ Mock이 '없음(None)'을 반환해야 중복 체크를 통과함
        mock_repo.get_user_by_email.return_value = None
        mock_repo.get_user_by_nickname.return_value = None
        mock_repo.get_user_by_phone_num.return_value = None

        request = SignUpRequest(
            email="new@test.com",
            password="password123",
            checked_password="password123",
            nickname="newuser",
            name="신규",
            phone_num="01012345678",
        )

        mock_repo.save_user.side_effect = lambda u: u

        with patch("core.security.hash_password", return_value="hashed_pw"):
            result = await service.sign_up(request)

        assert result.email == "new@test.com"
        mock_repo.save_user.assert_called_once()

    async def test_sign_up_duplicate_email(self, service, mock_repo):
        mock_repo.get_user_by_email.return_value = User(email="exist@test.com")
        request = SignUpRequest(
            email="exist@test.com",
            password="password123",
            checked_password="password123",
            nickname="nick",
        )
        with pytest.raises(DuplicateEmailException):
            await service.sign_up(request)

    async def test_sign_up_password_mismatch(self, service, mock_repo):
        mock_repo.get_user_by_email.return_value = None
        mock_repo.get_user_by_nickname.return_value = None
        request = SignUpRequest(
            email="test@test.com",
            password="password123",
            checked_password="different123",
            nickname="nick",
        )
        with pytest.raises(InvalidCheckedPasswordException):
            await service.sign_up(request)

    async def test_log_in_success(self, service, mock_repo, mock_redis):
        user_id = "user-uuid-123"
        mock_user = User(id=user_id, email="login@test.com", password="hashed_pw")
        mock_repo.get_user_by_email.return_value = mock_user
        request = LogInRequest(email="login@test.com", password="real_password")

        with (
            patch("core.security.verify_password", return_value=True),
            patch("core.security.create_jwt", return_value="fake_access_token"),
            patch("core.security.create_refresh_token", return_value="fake_refresh_token"),
        ):
            response = await service.log_in(request, req=None)

        assert response.access_token == "fake_access_token"
        assert response.refresh_token == "fake_refresh_token"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args[1]
        assert call_args["name"] == "RT:fake_refresh_token"
        assert call_args["value"] == user_id

    async def test_log_in_fail_wrong_password(self, service, mock_repo):
        mock_user = User(email="login@test.com", password="hashed_pw")
        mock_repo.get_user_by_email.return_value = mock_user
        request = LogInRequest(email="login@test.com", password="wrong_pw_123")

        with patch("core.security.verify_password", return_value=False):
            with pytest.raises(InvalidCredentialsException):
                await service.log_in(request, req=None)

    async def test_refresh_token_success(self, service, mock_redis):
        user_id = "user-uuid-123"
        mock_redis.get.return_value = user_id
        request = RefreshTokenRequest(refresh_token="valid_refresh_token")

        with patch("core.security.create_jwt", return_value="new_access_token"):
            response = await service.refresh_token(request)

        mock_redis.get.assert_called_once_with("RT:valid_refresh_token")
        assert response.access_token == "new_access_token"

    async def test_refresh_token_expired(self, service, mock_redis):
        mock_redis.get.return_value = None  # 토큰 없음
        request = RefreshTokenRequest(refresh_token="expired_token")

        with pytest.raises(TokenExpiredException):
            await service.refresh_token(request)

    # --- [수정된 로그아웃 테스트] ---

    async def test_log_out_success(self, service, mock_redis):
        """[Service] 본인 확인 후 로그아웃 성공"""
        user_id = "user-uuid-123"

        # 1. Redis에서 토큰 조회 시 "이 토큰의 주인은 user-uuid-123이다"라고 응답 설정
        mock_redis.get.return_value = user_id
        mock_redis.delete.return_value = 1

        request = LogOutRequest(refresh_token="valid_token")

        # 2. 내 아이디(user_id)를 넣어서 로그아웃 요청
        await service.log_out(request, user_id)

        # 3. 조회(get)와 삭제(delete)가 모두 호출되었는지 검증
        mock_redis.get.assert_called_once_with("RT:valid_token")
        mock_redis.delete.assert_called_once_with("RT:valid_token")

    async def test_log_out_fail_invalid_token(self, service, mock_redis):
        """[Service] 토큰이 존재하지 않거나 만료됨 -> 예외 발생"""
        # 1. Redis에 토큰이 없음 (None)
        mock_redis.get.return_value = None

        request = LogOutRequest(refresh_token="missing_token")

        # 2. 예외 발생 확인 (InvalidTokenException 사용 추천)
        with pytest.raises(TokenExpiredException):
            await service.log_out(request, "any_user_id")

    async def test_log_out_fail_forbidden(self, service, mock_redis):
        """[Service] 남의 토큰을 삭제하려고 함 -> 예외 발생"""
        # 1. Redis에는 "other_user"의 토큰이라고 저장되어 있음
        mock_redis.get.return_value = "other_user"

        request = LogOutRequest(refresh_token="others_token")

        # 2. 나는 "my_user"인데 삭제 시도 -> Forbidden 예외 발생
        with pytest.raises(TokenForbiddenException):
            await service.log_out(request, "my_user")
