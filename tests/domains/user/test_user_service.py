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

        # save_user 호출 시 들어온 객체 그대로 반환
        mock_repo.save_user.side_effect = lambda u: u

        with patch("core.security.hash_password", return_value="hashed_pw"):
            result = await service.sign_up(request)

        assert result.email == "new@test.com"
        mock_repo.save_user.assert_called_once()

    async def test_sign_up_duplicate_email(self, service, mock_repo):
        """[Service] 이메일 중복 시 예외 발생"""
        # 이미 존재하는 유저 반환
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
        """[Service] 비밀번호 불일치 예외 발생"""
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
        """[Service] 로그인 성공 (Redis 저장 확인)"""
        user_id = "user-uuid-123"
        mock_user = User(id=user_id, email="login@test.com", password="hashed_pw")
        mock_repo.get_user_by_email.return_value = mock_user

        request = LogInRequest(email="login@test.com", password="real_password")

        with (
            patch("core.security.verify_password", return_value=True),
            patch("core.security.create_jwt", return_value="fake_access_token"),
            patch(
                "core.security.create_refresh_token", return_value="fake_refresh_token"
            ),
        ):
            response = await service.log_in(request, req=None)

        # 1. 응답값 검증
        assert response.access_token == "fake_access_token"
        assert response.refresh_token == "fake_refresh_token"

        # 2. Redis 저장 호출 검증
        # redis.set(name="RT:fake_refresh_token", value="user-uuid-123", ex=...) 이 호출되어야 함
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args[1]  # 키워드 인자 가져오기
        assert call_args["name"] == "RT:fake_refresh_token"
        assert call_args["value"] == user_id

    async def test_log_in_fail_wrong_password(self, service, mock_repo):
        """[Service] 비밀번호 틀림 -> 예외 발생"""
        mock_user = User(email="login@test.com", password="hashed_pw")
        mock_repo.get_user_by_email.return_value = mock_user

        request = LogInRequest(email="login@test.com", password="wrong_pw_123")

        with patch("core.security.verify_password", return_value=False):
            with pytest.raises(InvalidCredentialsException):
                await service.log_in(request, req=None)

    # --- [추가] 리프레시 토큰 재발급 테스트 ---
    async def test_refresh_token_success(self, service, mock_redis):
        """[Service] 토큰 재발급 성공"""
        # Redis에서 꺼낼 유저 ID 설정
        user_id = "user-uuid-123"
        mock_redis.get.return_value = user_id

        request = RefreshTokenRequest(refresh_token="valid_refresh_token")

        with patch("core.security.create_jwt", return_value="new_access_token"):
            response = await service.refresh_token(request)

        # Redis 조회 확인
        mock_redis.get.assert_called_once_with("RT:valid_refresh_token")

        # 새 토큰 반환 확인
        assert response.access_token == "new_access_token"
        assert response.refresh_token == "valid_refresh_token"

    async def test_refresh_token_expired(self, service, mock_redis):
        """[Service] 만료된 토큰으로 재발급 시도 -> 예외 발생"""
        # Redis에 키가 없음 (None 반환)
        mock_redis.get.return_value = None

        request = RefreshTokenRequest(refresh_token="expired_token")

        with pytest.raises(TokenExpiredException):
            await service.refresh_token(request)

    # --- [추가] 로그아웃 테스트 ---
    async def test_log_out_success(self, service, mock_redis):
        """[Service] 로그아웃 성공"""
        # Redis delete가 1(삭제 성공)을 반환한다고 가정
        mock_redis.delete.return_value = 1

        request = LogOutRequest(refresh_token="valid_token")

        await service.log_out(request)

        mock_redis.delete.assert_called_once_with("RT:valid_token")

    async def test_log_out_fail_already_deleted(self, service, mock_redis):
        """[Service] 이미 삭제된 토큰으로 로그아웃 시도 -> 예외 발생"""
        # Redis delete가 0(삭제된 게 없음)을 반환한다고 가정
        mock_redis.delete.return_value = 0

        request = LogOutRequest(refresh_token="already_deleted_token")

        with pytest.raises(TokenExpiredException):
            await service.log_out(request)
