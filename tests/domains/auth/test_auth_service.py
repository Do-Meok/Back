from unittest.mock import AsyncMock, patch

import pytest

from domains.auth.exceptions import InvalidCredentialsException
from domains.auth.schemas.request import LogInRequest, LogOutRequest, RefreshTokenRequest
from domains.auth.service import AuthService
from domains.user.models import User


# --- Fixtures ---
@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def auth_service(mock_user_repo, mock_redis):
    return AuthService(user_repo=mock_user_repo, redis=mock_redis)


@pytest.fixture
def mock_user():
    user = User(email="test@example.com", password="hashed_password", nickname="tester", name="홍길동")
    user.id = "user_id_123"
    return user


# --- Tests ---
@pytest.mark.asyncio
async def test_log_in_success(auth_service, mock_user_repo, mock_redis, mock_user):
    """[Auth Service] 로그인 성공 및 토큰 발급"""
    mock_user_repo.get_user_by_email.return_value = mock_user
    request = LogInRequest(email="test@example.com", password="password123")

    # security.verify_password를 모킹해서 무조건 True를 반환하도록 설정
    with patch("domains.auth.service.security.verify_password", return_value=True):
        with patch("domains.auth.service.security.create_jwt", return_value="mock_access_token"):
            with patch("domains.auth.service.security.create_refresh_token", return_value="mock_refresh_token"):
                response = await auth_service.log_in(request)

                assert response.access_token == "mock_access_token"
                assert response.refresh_token == "mock_refresh_token"
                mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_log_in_fail_invalid_credentials(auth_service, mock_user_repo):
    """[Auth Service] 로그인 실패 (비밀번호 불일치)"""
    mock_user_repo.get_user_by_email.return_value = AsyncMock()  # 유저는 존재함
    request = LogInRequest(email="test@example.com", password="wrong_password")

    with patch("domains.auth.service.security.verify_password", return_value=False):
        with pytest.raises(InvalidCredentialsException):
            await auth_service.log_in(request)


@pytest.mark.asyncio
async def test_refresh_token_success(auth_service, mock_redis):
    """[Auth Service] 리프레시 토큰 재발급 성공"""
    mock_redis.get.return_value = b"user_id_123"
    request = RefreshTokenRequest(refresh_token="old_refresh_token")

    with patch("domains.auth.service.security.create_jwt", return_value="new_access_token"):
        with patch("domains.auth.service.security.create_refresh_token", return_value="new_refresh_token"):
            response = await auth_service.refresh_token(request)

            assert response.access_token == "new_access_token"
            mock_redis.delete.assert_called_once_with("RT:old_refresh_token")
            mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_log_out_success(auth_service, mock_redis):
    """[Auth Service] 로그아웃 성공 (Redis에서 토큰 삭제)"""
    mock_redis.get.return_value = b"user_id_123"
    request = LogOutRequest(refresh_token="valid_refresh_token")

    await auth_service.log_out(request, user_id="user_id_123")
    mock_redis.delete.assert_called_once_with("RT:valid_refresh_token")


@pytest.mark.asyncio
async def test_get_user_by_token_success(auth_service, mock_user_repo, mock_user):
    """[Auth Service] 토큰으로 유저 정보 가져오기"""
    mock_user_repo.get_user_by_id.return_value = mock_user

    with patch("domains.auth.service.security.decode_jwt", return_value="user_id_123"):
        user = await auth_service.get_user_by_token("mock_access_token")

        assert user.email == mock_user.email
