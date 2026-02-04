import pytest
from core import security

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
            "birth": "1990-01-01",  # [수정] YYYY-MM-DD 형식
            "phone_num": PHONE,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == EMAIL


@pytest.mark.asyncio
async def test_sign_up_duplicate_email(client):
    """[API] 이메일 중복 체크"""
    # 1. 먼저 가입
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

    # 2. 같은 이메일로 재가입 시도
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
async def test_log_in_flow(client):
    """[API] 회원가입 후 로그인 성공 테스트"""
    # 1. 가입
    login_email = "login_flow@test.com"
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": login_email,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "login_flow",
            "name": "flow",
        },
    )

    # 2. 로그인
    response = await client.post("/api/v1/users/log-in", json={"email": login_email, "password": PASSWORD})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_get_user_info(authorized_client):
    """[API] 내 정보 조회 (authorized_client 사용)"""
    response = await authorized_client.get("/api/v1/users/info")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["nickname"] == "테스트유저"


# --- [리프레시 토큰 및 로그아웃] ---


@pytest.mark.asyncio
async def test_refresh_token_success(client, mock_redis):
    """[API] 리프레시 토큰으로 액세스 토큰 재발급 성공"""
    # 1. 가입
    email = "refresh_success@test.com"
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": email,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "refresh_user",
            "name": "refresh",
        },
    )

    # 2. 로그인
    login_res = await client.post("/api/v1/users/log-in", json={"email": email, "password": PASSWORD})
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # [핵심] Redis에 토큰이 존재한다고 설정
    mock_redis.get.return_value = "some-user-id"

    # 3. 토큰 재발급 요청
    refresh_res = await client.post("/api/v1/users/refresh", json={"refresh_token": refresh_token})

    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "access_token" in new_data


@pytest.mark.asyncio
async def test_refresh_token_fail_invalid(client, mock_redis):
    """[API] 유효하지 않은 리프레시 토큰으로 요청 시 실패"""
    mock_redis.get.return_value = None

    response = await client.post(
        "/api/v1/users/refresh",
        json={"refresh_token": "invalid_or_expired_token_string"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_flow(client, mock_redis):
    """[API] 로그아웃 시나리오 (로그인 -> 헤더 포함 로그아웃 -> 재발급 실패 확인)"""
    # 1. 가입
    email = "logout_test@test.com"
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": email,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "logout_user",
            "name": "logout",
        },
    )

    # 2. 로그인
    login_res = await client.post("/api/v1/users/log-in", json={"email": email, "password": PASSWORD})
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 3. 로그아웃 요청 (헤더 포함 + Redis Mock 설정)
    user_id = security.decode_jwt(access_token)
    mock_redis.get.return_value = user_id

    logout_res = await client.post(
        "/api/v1/users/log-out",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert logout_res.status_code == 200

    # 4. 검증: 로그아웃된 토큰으로 재발급 시도 -> 실패
    mock_redis.get.return_value = None
    retry_refresh_res = await client.post("/api/v1/users/refresh", json={"refresh_token": refresh_token})

    assert retry_refresh_res.status_code == 401


# --- [추가된 API 테스트 (수정됨)] ---


@pytest.mark.asyncio
async def test_find_email_success(client):
    """[API] 이메일 찾기 성공"""
    # 1. 가입
    email = "find@test.com"
    name = "김찾기"
    birth = "1999-01-01"  # [수정] YYYY-MM-DD
    phone = "01011112222"  # 하이픈 없이 11자리 (스키마 length 제한 준수)

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

    # 2. 이메일 찾기 요청
    response = await client.post(
        "/api/v1/users/find-email",
        json={
            "name": name,
            "birth": birth,  # [수정] "1999-01-01" 전송
            "phone_num": phone,
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_find_email_fail_not_found(client):
    """[API] 정보 불일치로 이메일 찾기 실패"""
    # [수정] birth 형식을 맞춰줘야 422(Validation Error)가 아니라 404(Not Found)가 뜹니다.
    response = await client.post(
        "/api/v1/users/find-email",
        json={
            "name": "없는사람",
            "birth": "2000-01-01",  # [수정]
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

    # 1. 가입
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

    # 2. 로그인 (토큰 획득)
    login_res = await client.post("/api/v1/users/log-in", json={"email": email, "password": old_pw})
    access_token = login_res.json()["access_token"]

    # 3. 비밀번호 변경 요청
    change_res = await client.patch(
        "/api/v1/users/change-pw",
        json={
            # [수정] old_password -> current_password (스키마 일치)
            "current_password": old_pw,
            "new_password": new_pw,
            "checked_new_password": new_pw,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # 디버깅용 로그 (혹시 또 에러나면 확인용)
    if change_res.status_code == 422:
        print(change_res.json())

    assert change_res.status_code == 200

    # 4. 검증: 예전 비밀번호로 로그인 실패
    fail_login = await client.post("/api/v1/users/log-in", json={"email": email, "password": old_pw})
    assert fail_login.status_code == 401

    # 5. 검증: 새 비밀번호로 로그인 성공
    success_login = await client.post("/api/v1/users/log-in", json={"email": email, "password": new_pw})
    assert success_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_success(client):
    """[API] 비밀번호 재설정(초기화) 성공"""
    email = "reset@test.com"
    old_pw = "old_12345"
    new_pw = "reset_12345"
    name = "초기화"
    birth = "2000-01-01"  # [수정] YYYY-MM-DD
    phone = "01099998888"

    # 1. 가입
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

    # 2. 비밀번호 재설정 요청
    reset_res = await client.post(
        "/api/v1/users/reset-pw",
        json={
            "email": email,
            "name": name,
            "birth": birth,  # [수정] YYYY-MM-DD
            "phone_num": phone,
            "new_password": new_pw,
            "checked_new_password": new_pw,
        },
    )
    assert reset_res.status_code == 200

    # 3. 새 비밀번호로 로그인 성공 확인
    login_res = await client.post("/api/v1/users/log-in", json={"email": email, "password": new_pw})
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_change_nickname_flow(client):
    """[API] 닉네임 변경 및 중복 체크"""
    email = "nick@test.com"
    # 1. 가입
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

    # 로그인해서 토큰 받기
    login_res = await client.post("/api/v1/users/log-in", json={"email": email, "password": PASSWORD})
    access_token = login_res.json()["access_token"]

    # 2. 닉네임 변경 요청
    new_nick = "new_nick"
    res = await client.patch(
        "/api/v1/users/nickname", json={"nickname": new_nick}, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert res.status_code == 200
    assert res.json()["nickname"] == new_nick

    # 3. 변경 확인 (내 정보 조회)
    info_res = await client.get("/api/v1/users/info", headers={"Authorization": f"Bearer {access_token}"})
    assert info_res.json()["nickname"] == new_nick
