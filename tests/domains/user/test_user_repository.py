import pytest
from domains.user.models import User
from domains.user.repository import UserRepository


@pytest.mark.asyncio
async def test_save_user(db_session):
    """[Repository] 유저 저장 테스트"""
    repo = UserRepository(db_session)

    # Given
    user = User(
        email="repo_test@example.com",
        password="hashed_password",
        nickname="repo_nick",
        name="김테스트",
        social_auth="local",
    )

    # When
    saved_user = await repo.save_user(user)

    # Then
    assert saved_user.id is not None
    assert saved_user.email == "repo_test@example.com"


@pytest.mark.asyncio
async def test_find_by_email(db_session):
    """[Repository] 이메일로 유저 조회"""
    repo = UserRepository(db_session)

    # Given
    user = User(email="find@example.com", password="pw", nickname="finder", phone_hash="hash123")
    await repo.save_user(user)

    # When
    found_user = await repo.get_user_by_email("find@example.com")

    # Then
    assert found_user is not None
    assert found_user.nickname == "finder"


@pytest.mark.asyncio
async def test_find_by_phone_hash(db_session):
    """[Repository] 전화번호 해시로 유저 조회"""
    repo = UserRepository(db_session)

    # Given
    user = User(
        email="phone@example.com",
        password="pw",
        nickname="phoner",
        phone_hash="unique_hash_value",
    )
    await repo.save_user(user)

    # When
    found_user = await repo.get_user_by_phone_num("unique_hash_value")

    # Then
    assert found_user is not None
    assert found_user.email == "phone@example.com"
