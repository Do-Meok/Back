import pytest

# 테스트 데이터 상수
EMAIL = "api_test@example.com"
PASSWORD = "password123!"
NICKNAME = "api_tester"
PHONE = "01012345678"


@pytest.mark.asyncio
async def test_sign_up_success(client):
    """[API] 회원가입 성공"""
    response = await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": NICKNAME,
            "name": "홍길동",
            "birth": "1990-01-01",
            "phone_num": PHONE,
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == EMAIL


@pytest.mark.asyncio
async def test_sign_up_duplicate_email(client):
    """[API] 이메일 중복 체크"""
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": "dup@test.com",
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "dup_nick",
            "name": "dup",
        },
    )

    response = await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": "dup@test.com",
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "other_nick",
            "name": "other",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_CONFLICT"


@pytest.mark.asyncio
async def test_get_user_info(authorized_client):
    """[API] 내 정보 조회 (authorized_client 사용)"""
    response = await authorized_client.get("/api/v1/users/info")

    assert response.status_code == 200
    data = response.json()
    # authorized_client 설정에 따라 검증값 조정 필요
    assert data["email"] == "test@example.com"
    assert data["nickname"] == "테스트유저"


@pytest.mark.asyncio
async def test_find_email_success(client):
    """[API] 이메일 찾기 성공"""
    email = "find@test.com"
    name = "김찾기"
    birth = "1999-01-01"
    phone = "01011112222"

    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": email,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "find_nick",
            "name": name,
            "birth": birth,
            "phone_num": phone,
        },
    )

    response = await client.post(
        "/api/v1/users/find-email",
        json={
            "name": name,
            "birth": birth,
            "phone_num": phone,
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_find_email_fail_not_found(client):
    """[API] 정보 불일치로 이메일 찾기 실패"""
    response = await client.post(
        "/api/v1/users/find-email",
        json={
            "name": "없는사람",
            "birth": "2000-01-01",
            "phone_num": "01000000000",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_change_password_success(client):
    """[API] 비밀번호 변경 성공 시나리오"""
    email = "changepw@test.com"
    old_pw = "old_pass_123"
    new_pw = "new_pass_123"

    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": email,
            "password": old_pw,
            "checked_password": old_pw,
            "nickname": "change_pw_user",
            "name": "변경맨",
        },
    )

    # Auth API를 통해 로그인
    login_res = await client.post("/api/v1/auth/log-in", json={"email": email, "password": old_pw})
    access_token = login_res.json()["access_token"]

    change_res = await client.patch(
        "/api/v1/users/change-pw",
        json={
            "current_password": old_pw,
            "new_password": new_pw,
            "checked_new_password": new_pw,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert change_res.status_code == 200

    fail_login = await client.post("/api/v1/auth/log-in", json={"email": email, "password": old_pw})
    assert fail_login.status_code == 401

    success_login = await client.post("/api/v1/auth/log-in", json={"email": email, "password": new_pw})
    assert success_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_success(client):
    """[API] 비밀번호 재설정(초기화) 성공"""
    email = "reset@test.com"
    old_pw = "old_12345"
    new_pw = "reset_12345"
    name = "초기화"
    birth = "2000-01-01"
    phone = "01099998888"

    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": email,
            "password": old_pw,
            "checked_password": old_pw,
            "nickname": "reset_user",
            "name": name,
            "birth": birth,
            "phone_num": phone,
        },
    )

    reset_res = await client.post(
        "/api/v1/users/reset-pw",
        json={
            "email": email,
            "name": name,
            "birth": birth,
            "phone_num": phone,
            "new_password": new_pw,
            "checked_new_password": new_pw,
        },
    )
    assert reset_res.status_code == 200

    login_res = await client.post("/api/v1/auth/log-in", json={"email": email, "password": new_pw})
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_change_nickname_flow(client):
    """[API] 닉네임 변경 및 중복 체크"""
    email = "nick@test.com"
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": email,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "old_nick",
            "name": "닉네임맨",
        },
    )

    login_res = await client.post("/api/v1/auth/log-in", json={"email": email, "password": PASSWORD})
    access_token = login_res.json()["access_token"]

    new_nick = "new_nick"
    res = await client.patch(
        "/api/v1/users/nickname", json={"nickname": new_nick}, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert res.status_code == 200
    assert res.json()["nickname"] == new_nick

    info_res = await client.get("/api/v1/users/info", headers={"Authorization": f"Bearer {access_token}"})
    assert info_res.json()["nickname"] == new_nick
