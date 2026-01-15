import pytest
from unittest.mock import AsyncMock, patch
from domains.user.service import UserService
from domains.user.schemas import SignUpRequest, LogInRequest
from domains.user.exceptions import (
    DuplicateEmailException,
    InvalidCheckedPasswordException,
    InvalidCredentialsException,
)
from domains.user.models import User


@pytest.mark.asyncio
class TestUserService:
    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    async def test_sign_up_success(self, mock_repo):
        service = UserService(mock_repo)

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

    async def test_sign_up_duplicate_email(self, mock_repo):
        """[Service] 이메일 중복 시 예외 발생"""
        service = UserService(mock_repo)

        # 이미 존재하는 유저 반환
        mock_repo.get_user_by_email.return_value = User(email="exist@test.com")

        request = SignUpRequest(
            email="exist@test.com",
            password="password123",  # ✅ 8자 이상
            checked_password="password123",
            nickname="nick",
        )

        with pytest.raises(DuplicateEmailException):
            await service.sign_up(request)

    async def test_sign_up_password_mismatch(self, mock_repo):
        """[Service] 비밀번호 불일치 예외 발생"""
        service = UserService(mock_repo)

        mock_repo.get_user_by_email.return_value = None
        mock_repo.get_user_by_nickname.return_value = None

        request = SignUpRequest(
            email="test@test.com",
            password="password123",
            checked_password="different123",  # ✅ 8자 이상이고 서로 다름
            nickname="nick",
        )

        with pytest.raises(InvalidCheckedPasswordException):
            await service.sign_up(request)

    async def test_log_in_success(self, mock_repo):
        """[Service] 로그인 성공"""
        service = UserService(mock_repo)

        mock_user = User(id="user-id", email="login@test.com", password="hashed_pw")
        mock_repo.get_user_by_email.return_value = mock_user

        request = LogInRequest(
            email="login@test.com", password="real_password"
        )  # 8자 이상

        with (
            patch("core.security.verify_password", return_value=True),
            patch("core.security.create_jwt", return_value="fake_access_token"),
        ):
            response = await service.log_in(request, req=None)

        assert response.access_token == "fake_access_token"

    async def test_log_in_fail_wrong_password(self, mock_repo):
        """[Service] 비밀번호 틀림 -> 예외 발생"""
        service = UserService(mock_repo)

        mock_user = User(email="login@test.com", password="hashed_pw")
        mock_repo.get_user_by_email.return_value = mock_user

        request = LogInRequest(email="login@test.com", password="wrong_pw_123")

        with patch("core.security.verify_password", return_value=False):
            with pytest.raises(InvalidCredentialsException):
                await service.log_in(request, req=None)
