# tests/domains/user/test_user_api.py
import pytest
from httpx import AsyncClient

# 테스트 데이터 상수
EMAIL = "test@example.com"
PASSWORD = "password123!"
NICKNAME = "tester"
PHONE = "01012345678"


@pytest.mark.asyncio
async def test_sign_up_success(client: AsyncClient):
    # 1. 회원가입 성공 테스트
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
async def test_sign_up_duplicate_email(client: AsyncClient):
    # 2. 이메일 중복 시 409 에러 및 에러 코드 확인
    # (A) 먼저 한 명 가입
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "user1",
            "name": "user1",
            "birth": "1990-01-01",
            "phone_num": "01011112222",
        },
    )

    # (B) 같은 이메일로 가입 시도
    response = await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": EMAIL,  # 중복 이메일
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": "user2",
            "name": "user2",
            "birth": "1990-01-01",
            "phone_num": "01033334444",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_CONFLICT"


@pytest.mark.asyncio
async def test_sign_up_password_mismatch(client: AsyncClient):
    # 3. 비밀번호 확인 불일치 시 400 에러 확인
    response = await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": "mismatch@test.com",
            "password": "password123!",
            "checked_password": "different!!!",  # 다름
            "nickname": "mismatch",
            "name": "fail",
            "birth": "1990-01-01",
            "phone_num": "01099998888",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "PASSWORD_MISMATCH"  # 영훈님이 정의한 에러코드


@pytest.mark.asyncio
async def test_log_in_success(client: AsyncClient):
    # 4. 로그인 성공 테스트
    # (A) 가입
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": NICKNAME,
            "name": "login",
            "birth": "1990-01-01",
            "phone_num": PHONE,
        },
    )

    # (B) 로그인
    response = await client.post(
        "/api/v1/users/log-in", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_log_in_fail(client: AsyncClient):
    # 5. 로그인 실패 (비밀번호 틀림)
    # (A) 가입
    await client.post(
        "/api/v1/users/sign-up",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "checked_password": PASSWORD,
            "nickname": NICKNAME,
            "name": "login_fail",
            "birth": "1990-01-01",
            "phone_num": PHONE,
        },
    )

    # (B) 틀린 비번으로 로그인
    response = await client.post(
        "/api/v1/users/log-in", json={"email": EMAIL, "password": "wrong_password"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"

@pytest.mark.asyncio
async def test_get_user_info(authorized_client):
    response = await authorized_client.get("/api/v1/users/info")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["nickname"] == "테스트유저"
