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
    data = response.json()
    assert data["email"] == EMAIL
    assert data["message"] == "회원가입이 완료되었습니다."


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
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_get_user_info(authorized_client):
    """[API] 내 정보 조회 (authorized_client 사용)"""
    # authorized_client는 이미 가짜 로그인 상태임 (Fixture 참고)
    response = await authorized_client.get("/api/v1/users/info")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"  # Fixture에서 설정한 유저 정보
    assert data["nickname"] == "테스트유저"
