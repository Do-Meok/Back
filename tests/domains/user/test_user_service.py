import pytest
from datetime import date
from unittest.mock import AsyncMock, patch
from domains.user.service import UserService
from domains.user.schemas import (
    SignUpRequest,
    LogInRequest,
    RefreshTokenRequest,
    LogOutRequest,
    ChangeNicknameRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    FindEmailRequest,
)
from domains.user.exceptions import (
    DuplicateEmailException,
    InvalidCheckedPasswordException,
    InvalidCredentialsException,
    TokenExpiredException,
    TokenForbiddenException,
    DuplicateNicknameException,
    UserNotFoundException,
    PasswordUnchangedException,
    IncorrectPasswordException,
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
            checked_password="different123",  # 8자 이상
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
        mock_redis.get.return_value = None
        request = RefreshTokenRequest(refresh_token="expired_token")

        with pytest.raises(TokenExpiredException):
            await service.refresh_token(request)

    async def test_log_out_success(self, service, mock_redis):
        user_id = "user-uuid-123"
        mock_redis.get.return_value = user_id
        mock_redis.delete.return_value = 1
        request = LogOutRequest(refresh_token="valid_token")

        await service.log_out(request, user_id)

        mock_redis.get.assert_called_once_with("RT:valid_token")
        mock_redis.delete.assert_called_once_with("RT:valid_token")

    async def test_log_out_fail_invalid_token(self, service, mock_redis):
        mock_redis.get.return_value = None
        request = LogOutRequest(refresh_token="missing_token")

        with pytest.raises(TokenExpiredException):
            await service.log_out(request, "any_user_id")

    async def test_log_out_fail_forbidden(self, service, mock_redis):
        mock_redis.get.return_value = "other_user"
        request = LogOutRequest(refresh_token="others_token")

        with pytest.raises(TokenForbiddenException):
            await service.log_out(request, "my_user")

    async def test_find_email_success(self, service, mock_repo):
        mock_user = User(email="find@test.com")
        mock_repo.find_user_by_recovery_info.return_value = mock_user

        request = FindEmailRequest(name="김찾기", birth=date(1999, 1, 1), phone_num="01012345678")

        with patch("core.security.make_phone_hash", return_value="hashed_phone"):
            response = await service.find_email(request)

        assert response.email == "find@test.com"

    async def test_find_email_not_found(self, service, mock_repo):
        mock_repo.find_user_by_recovery_info.return_value = None

        request = FindEmailRequest(name="없음", birth=date(1999, 1, 1), phone_num="01012345678")

        with patch("core.security.make_phone_hash", return_value="hashed_phone"):
            with pytest.raises(UserNotFoundException):
                await service.find_email(request)

    # --- [비밀번호 변경 테스트 (수정됨: 8자 이상)] ---

    async def test_change_password_success(self, service, mock_repo):
        """[Service] 비밀번호 변경 성공"""
        user_id = "uid"
        mock_user = User(id=user_id, password="hashed_old_pw")
        mock_repo.get_user_by_id.return_value = mock_user

        request = ChangePasswordRequest(
            current_password="old_password",  # 8자 이상
            new_password="new_password",  # 8자 이상
            checked_new_password="new_password",  # 8자 이상
        )

        with (
            patch("core.security.verify_password") as mock_verify,
            patch("core.security.hash_password", return_value="hashed_new_pw"),
        ):
            mock_verify.side_effect = [True, False]
            await service.change_password(request, user_id)
            mock_repo.update_user.assert_called_once()
            assert mock_user.password == "hashed_new_pw"

    async def test_change_password_fail_wrong_current(self, service, mock_repo):
        """[Service] 현재 비밀번호 틀림 -> 예외"""
        mock_user = User(password="hashed_old")
        mock_repo.get_user_by_id.return_value = mock_user

        request = ChangePasswordRequest(
            current_password="wrong_password",  # 8자 이상
            new_password="new_password",  # 8자 이상
            checked_new_password="new_password",
        )

        with patch("core.security.verify_password", return_value=False):
            with pytest.raises(IncorrectPasswordException):
                await service.change_password(request, "uid")

    async def test_change_password_fail_same_as_old(self, service, mock_repo):
        """[Service] 새 비밀번호가 기존과 동일 -> 예외"""
        mock_user = User(password="hashed_old")
        mock_repo.get_user_by_id.return_value = mock_user

        request = ChangePasswordRequest(
            current_password="old_password",  # 8자 이상
            new_password="old_password",  # 8자 이상
            checked_new_password="old_password",
        )

        with patch("core.security.verify_password", return_value=True):
            with pytest.raises(PasswordUnchangedException):
                await service.change_password(request, "uid")

    # --- [비밀번호 재설정 테스트 (수정됨: 8자 이상)] ---

    async def test_reset_password_success(self, service, mock_repo):
        """[Service] 비밀번호 재설정 성공"""
        mock_user = User(
            email="reset@test.com",
            name="홍길동",
            birth=date(2000, 1, 1),
            phone_hash="hashed_phone",
            password="old_hashed_pw",
        )
        mock_repo.get_user_by_email.return_value = mock_user

        request = ResetPasswordRequest(
            email="reset@test.com",
            name="홍길동",
            birth=date(2000, 1, 1),
            phone_num="01012345678",
            new_password="new_password",  # 8자 이상
            checked_new_password="new_password",
        )

        with (
            patch("core.security.make_phone_hash", return_value="hashed_phone"),
            patch("core.security.verify_password", return_value=False),
            patch("core.security.hash_password", return_value="new_hashed_pw"),
        ):
            await service.reset_password(request)
            mock_repo.update_user.assert_called_once()
            assert mock_user.password == "new_hashed_pw"

    async def test_reset_password_fail_info_mismatch(self, service, mock_repo):
        """[Service] 입력 정보 불일치 -> 예외"""
        mock_user = User(email="test@test.com", name="김철수", phone_hash="hash")
        mock_repo.get_user_by_email.return_value = mock_user

        request = ResetPasswordRequest(
            email="test@test.com",
            name="홍길동",
            birth=date(2000, 1, 1),
            phone_num="01012345678",
            new_password="new_password",  # 8자 이상
            checked_new_password="new_password",
        )

        with patch("core.security.make_phone_hash", return_value="hash"):
            with pytest.raises(UserNotFoundException):
                await service.reset_password(request)

    async def test_change_nickname_success(self, service, mock_repo):
        user_id = "uid"
        mock_user = User(id=user_id, nickname="old_nick")
        mock_repo.get_user_by_id.return_value = mock_user
        mock_repo.get_user_by_nickname.return_value = None

        request = ChangeNicknameRequest(nickname="new_nick")

        await service.change_nickname(request, user_id)

        mock_repo.update_user.assert_called_once()
        assert mock_user.nickname == "new_nick"

    async def test_change_nickname_fail_same(self, service, mock_repo):
        mock_user = User(id="uid", nickname="same_nick")
        mock_repo.get_user_by_id.return_value = mock_user

        request = ChangeNicknameRequest(nickname="same_nick")

        with pytest.raises(DuplicateNicknameException) as exc:
            await service.change_nickname(request, "uid")
        assert exc.value.detail == "현재 닉네임과 동일합니다."

    async def test_change_nickname_fail_duplicate(self, service, mock_repo):
        mock_user = User(id="uid", nickname="old_nick")
        mock_repo.get_user_by_id.return_value = mock_user
        mock_repo.get_user_by_nickname.return_value = User(nickname="taken_nick")

        request = ChangeNicknameRequest(nickname="taken_nick")

        with pytest.raises(DuplicateNicknameException) as exc:
            await service.change_nickname(request, "uid")
        assert exc.value.detail == "이미 사용 중인 닉네임입니다."
