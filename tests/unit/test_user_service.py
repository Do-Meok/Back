from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import uuid6

from core import security
from core.exception.exceptions import (
    BadRequestException,
    ConflictException,
    UnAuthorizedException,
    UserNotFoundException,
)
from domains.user.model import User
from domains.user.schemas import UpdatePasswordRequest, UpdateUserRequest
from domains.user.service import UserService


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def refresh_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user() -> User:
    return User(
        id=uuid6.uuid7(),
        email="test@example.com",
        password=security.hash_password("old-password"),
        nickname="testuser",
        name="테스트유저",
        birth=date(1990, 1, 1),
    )


@pytest.fixture
def user_service(user_repo: AsyncMock, refresh_store: AsyncMock) -> UserService:
    return UserService(user_repo=user_repo, refresh_store=refresh_store)


async def test_get_user_info_returns_profile(user_service: UserService, user_repo: AsyncMock, user: User):
    user_repo.get_user_by_id.return_value = user

    result = await user_service.get_user_info(user.id)

    assert result.nickname == "testuser"
    user_repo.get_user_by_id.assert_awaited_once_with(user.id)


async def test_get_user_info_raises_when_not_found(user_service: UserService, user_repo: AsyncMock):
    user_repo.get_user_by_id.return_value = None

    with pytest.raises(UserNotFoundException):
        await user_service.get_user_info(uuid6.uuid7())


async def test_update_user_rejects_same_nickname(user_service: UserService, user: User):
    with pytest.raises(ConflictException):
        await user_service.update_user(user, UpdateUserRequest(nickname="testuser"))


async def test_update_user_rejects_nickname_used_by_other_user(
    user_service: UserService, user_repo: AsyncMock, user: User
):
    other = User(id=uuid6.uuid7(), email="other@example.com", nickname="taken")
    user_repo.get_user_by_nickname.return_value = other

    with pytest.raises(ConflictException):
        await user_service.update_user(user, UpdateUserRequest(nickname="taken"))


async def test_update_user_updates_nickname_when_available(
    user_service: UserService, user_repo: AsyncMock, user: User
):
    user_repo.get_user_by_nickname.return_value = None

    result = await user_service.update_user(user, UpdateUserRequest(nickname="newnick"))

    assert user.nickname == "newnick"
    assert result.nickname == "newnick"
    user_repo.save_user.assert_awaited_once_with(user)


async def test_update_password_rejects_same_password(user_service: UserService, user: User):
    request = UpdatePasswordRequest(
        current_password="old-password",
        new_password="old-password",
        checked_new_password="old-password",
    )

    with pytest.raises(BadRequestException):
        await user_service.update_password(user, request)


async def test_update_password_requires_current_password_when_missing(user_service: UserService, user: User):
    # UpdatePasswordRequest는 min_length=8이라 빈 문자열을 만들 수 없어, 서비스의 방어 로직만 별도로 검증함
    request = SimpleNamespace(current_password="", new_password="new-password")

    with pytest.raises(BadRequestException):
        await user_service.update_password(user, request)


async def test_update_password_rejects_wrong_current_password(user_service: UserService, user: User):
    request = UpdatePasswordRequest(
        current_password="wrong-password",
        new_password="new-password",
        checked_new_password="new-password",
    )

    with pytest.raises(UnAuthorizedException):
        await user_service.update_password(user, request)


async def test_update_password_updates_and_revokes_sessions(
    user_service: UserService, user_repo: AsyncMock, refresh_store: AsyncMock, user: User
):
    request = UpdatePasswordRequest(
        current_password="old-password",
        new_password="new-password",
        checked_new_password="new-password",
    )

    await user_service.update_password(user, request)

    assert security.verify_password("new-password", user.password)
    user_repo.save_user.assert_awaited_once_with(user)
    refresh_store.revoke_all_for_user.assert_awaited_once_with(user.id)


async def test_update_password_skips_verification_for_social_login_user(
    user_service: UserService, user_repo: AsyncMock, user: User
):
    user.password = None
    request = UpdatePasswordRequest(
        current_password="whatever1",
        new_password="new-password",
        checked_new_password="new-password",
    )

    await user_service.update_password(user, request)

    assert security.verify_password("new-password", user.password)
