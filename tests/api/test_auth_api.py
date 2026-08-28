import pytest
from httpx import AsyncClient

from core.exception.codes import ErrorCode


# --- Fixtures ---
@pytest.fixture
def default_signup_payload() -> dict:
    return {
        "email": "user@example.com",
        "password": "password123",
        "checked_password": "password123",
        "nickname": "defaultuser",
    }


@pytest.fixture
async def registered_user(client: AsyncClient, default_signup_payload: dict) -> dict:
    """회원가입 후 가입 정보와 토큰을 반환하는 Fixture"""
    response = await client.post("/api/v1/users/sign-up", json=default_signup_payload)
    return response.json()


@pytest.fixture
def auth_headers(registered_user: dict) -> dict:
    """인증이 필요한 요청을 위한 Bearer Token 헤더 Fixture"""
    access_token = registered_user["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


# ==========================================
# 1. 회원가입 (Sign-Up) 테스트
# ==========================================

async def test_signup_success(client: AsyncClient, default_signup_payload: dict):
    response = await client.post("/api/v1/users/sign-up", json=default_signup_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["info"]["email"] == default_signup_payload["email"]
    assert body["info"]["nickname"] == default_signup_payload["nickname"]
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.parametrize(
    "initial_payload, request_payload, expected_status, expected_code",
    [
        # 이메일 중복
        (
            {"email": "dup@example.com", "password": "password", "checked_password": "password", "nickname": "user1"},
            {"email": "dup@example.com", "password": "password", "checked_password": "password", "nickname": "user2"},
            409,
            ErrorCode.EMAIL_CONFLICT,
        ),
        # 닉네임 중복
        (
            {"email": "user1@example.com", "password": "password", "checked_password": "password", "nickname": "same_nick"},
            {"email": "user2@example.com", "password": "password", "checked_password": "password", "nickname": "same_nick"},
            409,
            ErrorCode.NICKNAME_CONFLICT,
        ),
        # 비밀번호 불일치 (사전 등록 불필요)
        (
            None,
            {"email": "mismatch@example.com", "password": "password1", "checked_password": "password2", "nickname": "user3"},
            400,
            ErrorCode.PASSWORD_MISMATCH,
        ),
    ],
)
async def test_signup_validation_failures(
    client: AsyncClient,
    initial_payload: dict | None,
    request_payload: dict,
    expected_status: int,
    expected_code: ErrorCode,
):
    if initial_payload:
        await client.post("/api/v1/users/sign-up", json=initial_payload)

    response = await client.post("/api/v1/users/sign-up", json=request_payload)

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code


# ==========================================
# 2. 로그인 및 토큰 (Auth) 테스트
# ==========================================

async def test_login_success(client: AsyncClient, default_signup_payload: dict):
    await client.post("/api/v1/users/sign-up", json=default_signup_payload)

    response = await client.post(
        "/api/v1/auth/log-in",
        json={"email": default_signup_payload["email"], "password": default_signup_payload["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password_returns_unauthorized(client: AsyncClient, default_signup_payload: dict):
    await client.post("/api/v1/users/sign-up", json=default_signup_payload)

    response = await client.post(
        "/api/v1/auth/log-in",
        json={"email": default_signup_payload["email"], "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.UNAUTHORIZED


async def test_refresh_rotates_and_rejects_reuse(client: AsyncClient, registered_user: dict):
    old_refresh = registered_user["refresh_token"]

    # 정상 토큰 갱신
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != old_refresh

    # 기존 토큰 재사용 시도 차단
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401
    assert reuse.json()["code"] == ErrorCode.INVALID_TOKEN


async def test_logout_invalidates_refresh(client: AsyncClient, registered_user: dict):
    refresh = registered_user["refresh_token"]

    logout = await client.post("/api/v1/auth/log-out", json={"refresh_token": refresh})
    assert logout.status_code == 200

    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert again.status_code == 401


# ==========================================
# 3. 유저 프로필 및 비밀번호 변경 (/users/me) 테스트
# ==========================================

async def test_get_my_info(client: AsyncClient, auth_headers: dict, default_signup_payload: dict):
    response = await client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == default_signup_payload["email"]


async def test_update_nickname_success(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/v1/users/me",
        json={"nickname": "new_nickname"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["nickname"] == "new_nickname"


async def test_update_password_and_revoke_tokens(
    client: AsyncClient, auth_headers: dict, registered_user: dict, default_signup_payload: dict
):
    # 비밀번호 변경 요청
    response = await client.patch(
        "/api/v1/users/me/password",
        json={
            "current_password": default_signup_payload["password"],
            "new_password": "newpassword123!",
            "checked_new_password": "newpassword123!",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    # 핵심 검증: 비밀번호 변경 후 기존 Refresh Token이 무효화되었는지 확인
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert refresh_response.status_code in (401, 403)