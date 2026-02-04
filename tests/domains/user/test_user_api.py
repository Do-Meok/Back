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
            "birth": "1990-01-01",
            "phone_num": PHONE,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == EMAIL
    # 응답 모델에 message가 없다면 아래 줄은 에러가 날 수 있으니,
    # SignUpResponse 스키마에 message가 없다면 주석 처리하세요.
    # assert data["message"] == "회원가입이 완료되었습니다."


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
            "email": "dup@test.com",  # 중복
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
    response = await client.post(
        "/api/v1/users/log-in", json={"email": login_email, "password": PASSWORD}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data  # 리프레시 토큰 발급 확인


@pytest.mark.asyncio
async def test_get_user_info(authorized_client):
    """[API] 내 정보 조회 (authorized_client 사용)"""
    # authorized_client는 이미 가짜 로그인 상태임 (Fixture 참고)
    response = await authorized_client.get("/api/v1/users/info")

    assert response.status_code == 200
    data = response.json()
    # Fixture에서 설정한 유저 정보와 일치하는지 확인
    assert data["email"] == "test@example.com"
    assert data["nickname"] == "테스트유저"


# --- [추가된 테스트: 리프레시 토큰 및 로그아웃] ---


@pytest.mark.asyncio
async def test_refresh_token_success(client):
    """[API] 리프레시 토큰으로 액세스 토큰 재발급 성공"""
    # 1. 테스트용 유저 가입
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

    # 2. 로그인하여 토큰 발급
    login_res = await client.post(
        "/api/v1/users/log-in", json={"email": email, "password": PASSWORD}
    )
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # 3. 토큰 재발급 요청 (/refresh)
    refresh_res = await client.post(
        "/api/v1/users/refresh", json={"refresh_token": refresh_token}
    )

    assert refresh_res.status_code == 200
    new_data = refresh_res.json()

    # 4. 검증: 새로운 액세스 토큰이 발급되었는지 확인
    assert "access_token" in new_data
    assert new_data["access_token"] != ""


@pytest.mark.asyncio
async def test_refresh_token_fail_invalid(
    client, mock_redis
):  # [수정] mock_redis 인자 추가
    """[API] 유효하지 않은 리프레시 토큰으로 요청 시 실패"""

    # [핵심] 이 테스트에서는 Redis가 "모르는 토큰이다(None)"라고 답하게 설정
    mock_redis.get.return_value = None

    response = await client.post(
        "/api/v1/users/refresh",
        json={"refresh_token": "invalid_or_expired_token_string"},
    )

    # 이제 Redis가 없다고 했으니 401이 뜰 것입니다.
    assert response.status_code == 401


# 2. 로그아웃 플로우 테스트 수정
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

    # 2. 로그인 (Access Token, Refresh Token 모두 확보)
    login_res = await client.post(
        "/api/v1/users/log-in",
        json={"email": email, "password": PASSWORD}
    )
    tokens = login_res.json()
    access_token = tokens["access_token"]  # [헤더용]
    refresh_token = tokens["refresh_token"]  # [바디용]

    # -------------------------------------------------------------
    # [핵심] DB 조회 없이 토큰을 까서 User ID 확인 (Clean Way)
    # -------------------------------------------------------------
    user_id = security.decode_jwt(access_token)

    # 서비스 로직(본인 확인) 통과를 위해 Mock Redis가 "이 토큰 주인은 얘야"라고 응답하게 설정
    mock_redis.get.return_value = user_id

    # 3. 로그아웃 요청
    # [핵심] Authorization 헤더 추가 (current_user 의존성 해결)
    logout_res = await client.post(
        "/api/v1/users/log-out",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "로그아웃 되었습니다."

    # 4. 검증: 로그아웃된 토큰으로 재발급 시도 -> 실패해야 함
    # 로그아웃 후에는 Redis에 데이터가 없어야 하므로 None 반환 설정
    mock_redis.get.return_value = None

    retry_refresh_res = await client.post(
        "/api/v1/users/refresh",
        json={"refresh_token": refresh_token}
    )

    assert retry_refresh_res.status_code == 401