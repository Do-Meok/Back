import pytest
from datetime import date

from core.exception.exceptions import DatabaseException
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


@pytest.mark.asyncio
async def test_find_user_by_recovery_info(db_session):
    """[Repository] 이름, 생년월일, 전화번호 해시로 유저 조회"""
    repo = UserRepository(db_session)

    # Given: 테스트 유저 저장
    name = "김회복"
    birth = date(1995, 5, 5)
    phone_hash = "hashed_recovery_phone"

    user = User(
        email="recovery@test.com",
        password="pw",
        nickname="recover_nick",
        name=name,
        birth=birth,
        phone_hash=phone_hash,
    )
    await repo.save_user(user)

    # When 1: 모든 정보가 일치하는 경우
    found_user = await repo.find_user_by_recovery_info(name, birth, phone_hash)

    # Then 1: 유저 반환 성공
    assert found_user is not None
    assert found_user.email == "recovery@test.com"

    # When 2: 정보가 하나라도 틀린 경우 (예: 이름 불일치)
    not_found = await repo.find_user_by_recovery_info("박틀림", birth, phone_hash)

    # Then 2: None 반환
    assert not_found is None


@pytest.mark.asyncio
async def test_update_user_success(db_session):
    """[Repository] 유저 정보 업데이트 성공"""
    repo = UserRepository(db_session)

    # Given: 유저 생성
    user = User(
        email="update@test.com",
        password="old_password",
        nickname="old_nick",
    )
    saved_user = await repo.save_user(user)

    # When: 객체 수정 후 update_user 호출
    saved_user.nickname = "new_nick"
    saved_user.password = "new_password"

    await repo.update_user(saved_user)

    # Then: 세션 refresh 확인 및 DB 재조회 검증
    assert saved_user.nickname == "new_nick"

    # DB에서 다시 조회해서 확실히 커밋되었는지 확인
    reloaded_user = await repo.get_user_by_email("update@test.com")
    assert reloaded_user.nickname == "new_nick"
    assert reloaded_user.password == "new_password"


@pytest.mark.asyncio
async def test_update_user_fail_integrity_error(db_session):
    """[Repository] 업데이트 중 DB 제약조건 위반 시 예외 발생"""
    repo = UserRepository(db_session)

    # Given: 유저 A, 유저 B 생성
    user_a = User(email="a@test.com", nickname="unique_nick_a", password="pw")
    user_b = User(email="b@test.com", nickname="unique_nick_b", password="pw")

    await repo.save_user(user_a)
    user_b_saved = await repo.save_user(user_b)

    # When: 유저 B의 닉네임을 유저 A와 똑같이 변경 시도 (Unique 제약 위반 유도)
    user_b_saved.nickname = "unique_nick_a"

    # Then: DatabaseException 발생 확인
    with pytest.raises(DatabaseException):
        await repo.update_user(user_b_saved)
