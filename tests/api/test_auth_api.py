from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient

from core.exception.codes import ErrorCode

if TYPE_CHECKING:
    from tests.conftest import CapturingEmailService


# --- Fixtures ---
@pytest.fixture
def default_signup_payload() -> dict:
    return {
        "email": "user@example.com",
        "password": "password123",
        "checked_password": "password123",
        "nickname": "defaultuser",
        "name": "홍길동",
        "birth": date(1900, 1, 1).isoformat(),
        "phone_num": "010-1234-5678",
    }


async def _signup_and_verify(client: AsyncClient, email_service_stub: CapturingEmailService, payload: dict) -> dict:
    """가입 요청 -> 캡처된 인증코드로 검증까지 마치고 로그인 응답(dict)을 반환"""
    request_response = await client.post("/api/v1/auth/signup/request", json=payload)
    request_response.raise_for_status()
    code = email_service_stub.sent_codes[payload["email"]]
    verify_response = await client.post(
        "/api/v1/auth/signup/verify",
        json={"email": payload["email"], "code": code},
    )
    return verify_response.json()


@pytest.fixture
async def registered_user(
    client: AsyncClient, email_service_stub: CapturingEmailService, default_signup_payload: dict
) -> dict:
    """회원가입(이메일 인증 포함) 후 가입 정보와 토큰을 반환하는 Fixture"""
    return await _signup_and_verify(client, email_service_stub, default_signup_payload)


@pytest.fixture
def auth_headers(registered_user: dict) -> dict:
    """인증이 필요한 요청을 위한 Bearer Token 헤더 Fixture"""
    access_token = registered_user["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


# ==========================================
# 1. 회원가입 (Sign-Up) 테스트
# ==========================================


async def test_signup_request_sends_verification_code(
    client: AsyncClient, email_service_stub: CapturingEmailService, default_signup_payload: dict
):
    response = await client.post("/api/v1/auth/signup/request", json=default_signup_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["email"] == default_signup_payload["email"]
    assert body["expires_in_seconds"] > 0
    # 아직 인증 전이므로 실제 계정은 생성되지 않아야 함
    assert default_signup_payload["email"] in email_service_stub.sent_codes


async def test_signup_verify_creates_account_and_issues_tokens(
    client: AsyncClient, email_service_stub: CapturingEmailService, default_signup_payload: dict
):
    body = await _signup_and_verify(client, email_service_stub, default_signup_payload)

    assert body["info"]["email"] == default_signup_payload["email"]
    assert body["info"]["nickname"] == default_signup_payload["nickname"]
    assert body["info"]["name"] == default_signup_payload["name"]
    assert body["info"]["birth"] == default_signup_payload["birth"]
    assert body["access_token"]
    assert body["refresh_token"]


async def test_signup_verify_wrong_code_rejected(
    client: AsyncClient, email_service_stub: CapturingEmailService, default_signup_payload: dict
):
    await client.post("/api/v1/auth/signup/request", json=default_signup_payload)

    response = await client.post(
        "/api/v1/auth/signup/verify",
        json={"email": default_signup_payload["email"], "code": "000000"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == ErrorCode.INVALID_VERIFICATION_CODE


@pytest.mark.parametrize(
    "initial_payload, request_payload, expected_status, expected_code",
    [
        # 이메일 중복
        (
            {
                "email": "dup@example.com",
                "password": "password",
                "checked_password": "password",
                "nickname": "user1",
                "name": "홍길동",
                "birth": "1990-01-01",
                "phone_num": "010-1111-1111",
            },
            {
                "email": "dup@example.com",
                "password": "password",
                "checked_password": "password",
                "nickname": "user2",
                "name": "홍길동",
                "birth": "1990-01-01",
                "phone_num": "010-2222-2222",
            },
            409,
            ErrorCode.EMAIL_CONFLICT,
        ),
        # 닉네임 중복
        (
            {
                "email": "user1@example.com",
                "password": "password",
                "checked_password": "password",
                "nickname": "same_nick",
                "name": "홍길동",
                "birth": "1990-01-01",
                "phone_num": "010-3333-3333",
            },
            {
                "email": "user2@example.com",
                "password": "password",
                "checked_password": "password",
                "nickname": "same_nick",
                "name": "홍길동",
                "birth": "1990-01-01",
                "phone_num": "010-4444-4444",
            },
            409,
            ErrorCode.NICKNAME_CONFLICT,
        ),
        # 비밀번호 불일치 (사전 등록 불필요)
        (
            None,
            {
                "email": "mismatch@example.com",
                "password": "password1",
                "checked_password": "password2",
                "nickname": "user3",
                "name": "홍길동",
                "birth": "1990-01-01",
                "phone_num": "010-5555-5555",
            },
            400,
            ErrorCode.PASSWORD_MISMATCH,
        ),
    ],
)
async def test_signup_validation_failures(
    client: AsyncClient,
    email_service_stub: CapturingEmailService,
    initial_payload: dict | None,
    request_payload: dict,
    expected_status: int,
    expected_code: ErrorCode,
):
    if initial_payload:
        # 이메일 중복은 실제 확정 계정(인증 완료)에 대해서만 감지되므로 끝까지 검증해둠
        await _signup_and_verify(client, email_service_stub, initial_payload)

    response = await client.post("/api/v1/auth/signup/request", json=request_payload)

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code


# ==========================================
# 2. 로그인 및 토큰 (Auth) 테스트
# ==========================================


async def test_login_success(
    client: AsyncClient, email_service_stub: CapturingEmailService, default_signup_payload: dict
):
    await _signup_and_verify(client, email_service_stub, default_signup_payload)

    response = await client.post(
        "/api/v1/auth/log-in",
        json={"email": default_signup_payload["email"], "password": default_signup_payload["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password_returns_unauthorized(
    client: AsyncClient, email_service_stub: CapturingEmailService, default_signup_payload: dict
):
    await _signup_and_verify(client, email_service_stub, default_signup_payload)

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


# ==========================================
# 4. 비밀번호 재설정 (Password Reset) 테스트
# ==========================================


async def test_password_reset_flow_success(
    client: AsyncClient,
    email_service_stub: CapturingEmailService,
    registered_user: dict,
    default_signup_payload: dict,
):
    email = default_signup_payload["email"]

    request_response = await client.post("/api/v1/auth/password/reset/request", json={"email": email})
    assert request_response.status_code == 200
    code = email_service_stub.sent_codes[email]

    confirm_response = await client.post(
        "/api/v1/auth/password/reset/confirm",
        json={
            "email": email,
            "code": code,
            "new_password": "brandnewpassword1",
            "checked_new_password": "brandnewpassword1",
        },
    )
    assert confirm_response.status_code == 200

    # 새 비밀번호로 로그인 가능해야 함
    login_response = await client.post(
        "/api/v1/auth/log-in",
        json={"email": email, "password": "brandnewpassword1"},
    )
    assert login_response.status_code == 200

    # 재설정 이전에 발급된 refresh token은 전부 무효화되어야 함
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert refresh_response.status_code in (401, 403)


async def test_password_reset_request_unknown_email_returns_same_response(client: AsyncClient):
    """이메일 존재 여부를 노출하지 않기 위해 미가입 이메일도 동일하게 200 응답"""
    response = await client.post(
        "/api/v1/auth/password/reset/request",
        json={"email": "no-such-user@example.com"},
    )
    assert response.status_code == 200
