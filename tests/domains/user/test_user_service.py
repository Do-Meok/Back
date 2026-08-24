from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domains.user.exceptions import DuplicateEmailException, PasswordMismatchException
from domains.user.models import User
from domains.user.schemas.request import ChangeNicknameRequest, ChangePasswordRequest, FindEmailRequest, SignUpRequest
from domains.user.schemas.response import SignUpResponse
from domains.user.service import UserService


# --- Fixtures ---
@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def user_service(mock_user_repo):
    return UserService(user_repo=mock_user_repo)


@pytest.fixture
def mock_user():
    user = User(
        email="test@example.com", password="hashed_password", nickname="tester", name="홍길동", birth="1990-01-01"
    )
    user.id = "user_id_123"
    return user


# --- Tests ---
@pytest.mark.asyncio
async def test_sign_up_success(user_service, mock_user_repo):
    """[User Service] 회원가입 성공"""
    # 중복 검사 통과 설정 (None 반환)
    mock_user_repo.get_user_by_email.return_value = None
    mock_user_repo.get_user_by_nickname.return_value = None

    # 2. save_user가 .email 속성을 가진 객체를 반환하도록 설정 (중요!)
    # 문자열 "saved_user_object" 대신 Mock 객체나 User 인스턴스 사용
    test_email = "new@test.com"
    mock_saved_user = MagicMock(spec=User)
    mock_saved_user.email = test_email
    mock_user_repo.save_user.return_value = mock_saved_user

    request = SignUpRequest(
        email="new@test.com",
        password="password123!",
        checked_password="password123!",
        nickname="new_tester",
        name="신규유저",
        birth="2000-01-01",
    )

    with patch("domains.user.service.security.hash_password", return_value="hashed_pwd"):
        result = await user_service.sign_up(request)
        # 3. 검증: 결과는 SignUpResponse 타입이어야 함
        assert isinstance(result, SignUpResponse)
        assert result.email == test_email
        assert result.message == "회원가입이 완료되었습니다."

        # 레포지토리 호출 확인
        mock_user_repo.save_user.assert_called_once()


@pytest.mark.asyncio
async def test_sign_up_duplicate_email(user_service, mock_user_repo, mock_user):
    """[User Service] 회원가입 실패 (이메일 중복)"""
    mock_user_repo.get_user_by_email.return_value = mock_user  # 이미 유저 존재

    request = SignUpRequest(
        email="test@example.com",
        password="password123!",
        checked_password="password123!",
        nickname="tester2",
        name="홍길동",
        birth="1990-01-01",
    )

    with pytest.raises(DuplicateEmailException):
        await user_service.sign_up(request)


@pytest.mark.asyncio
async def test_find_email_success(user_service, mock_user_repo, mock_user):
    """[User Service] 이메일 찾기 성공"""
    mock_user_repo.find_user_by_recovery_info.return_value = mock_user

    request = FindEmailRequest(name="홍길동", birth="1990-01-01", phone_num="01012345678")

    with patch("domains.user.service.security.make_phone_hash", return_value="hashed_phone"):
        response = await user_service.find_email(request)
        assert response.email == mock_user.email


@pytest.mark.asyncio
async def test_change_password_mismatch(user_service, mock_user_repo, mock_user):
    """[User Service] 비밀번호 변경 실패 (새 비밀번호 확인 불일치)"""
    mock_user_repo.get_user_by_id.return_value = mock_user

    request = ChangePasswordRequest(
        current_password="old_password",
        new_password="new_password_1",
        checked_new_password="new_password_2",  # 불일치
    )

    with patch("domains.user.service.security.verify_password", side_effect=[True, False]):
        # side_effect: 첫 번째 호출(기존비번검증)은 True, 두 번째 호출(새비번중복검증)은 False 반환
        with pytest.raises(PasswordMismatchException):
            await user_service.change_password(request, user_id="user_id_123")


@pytest.mark.asyncio
async def test_change_nickname_success(user_service, mock_user_repo, mock_user):
    """[User Service] 닉네임 변경 성공"""
    mock_user_repo.get_user_by_id.return_value = mock_user
    mock_user_repo.get_user_by_nickname.return_value = None  # 변경하려는 닉네임이 중복되지 않음

    request = ChangeNicknameRequest(nickname="brand_new_nick")

    await user_service.change_nickname(request, user_id="user_id_123")

    assert mock_user.nickname == "brand_new_nick"
    mock_user_repo.update_user.assert_called_once_with(mock_user)
