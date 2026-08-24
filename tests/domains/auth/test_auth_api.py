from unittest.mock import AsyncMock

import pytest

from core import security
from api.v1.deps import get_social_auth_service
from main import app

PASSWORD = "password123!"


@pytest.mark.asyncio
async def test_log_in_flow(client):
    """[API] 회원가입 후 로그인 성공 테스트"""
    # 1. 가입 (User API 사용)
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

    # 2. 로그인 (Auth API 사용)
    response = await client.post("/api/v1/auth/log-in", json={"email": login_email, "password": PASSWORD})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_success(client, mock_redis):
    """[API] 리프레시 토큰으로 액세스 토큰 재발급 성공"""
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

    login_res = await client.post("/api/v1/auth/log-in", json={"email": email, "password": PASSWORD})
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    mock_redis.get.return_value = "some-user-id"

    # 3. 토큰 재발급 요청
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "access_token" in new_data


@pytest.mark.asyncio
async def test_refresh_token_fail_invalid(client, mock_redis):
    """[API] 유효하지 않은 리프레시 토큰으로 요청 시 실패"""
    mock_redis.get.return_value = None

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_or_expired_token_string"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_flow(client, mock_redis):
    """[API] 로그아웃 시나리오 (로그인 -> 헤더 포함 로그아웃 -> 재발급 실패 확인)"""
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

    login_res = await client.post("/api/v1/auth/log-in", json={"email": email, "password": PASSWORD})
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    user_id = security.decode_jwt(access_token)
    mock_redis.get.return_value = user_id

    # 3. 로그아웃 요청
    logout_res = await client.post(
        "/api/v1/auth/log-out",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert logout_res.status_code == 200

    mock_redis.get.return_value = None
    retry_refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert retry_refresh_res.status_code == 401


@pytest.mark.asyncio
async def test_get_kakao_url(client):
    """[API] 카카오 로그인 URL 반환 테스트 (모킹)"""
    # 1. 의존성 모킹 (SocialAuthService)
    mock_social_auth_service = AsyncMock()
    mock_auth_url = (
        "https://kauth.kakao.com/oauth/authorize?client_id=dummy_client_id&redirect_uri=dummy_uri&response_type=code"
    )
    mock_social_auth_service.get_kakao_auth_url.return_value = mock_auth_url

    # FastAPI dependency_overrides를 통해 주입될 서비스 교체
    app.dependency_overrides[get_social_auth_service] = lambda: mock_social_auth_service

    # 2. API 호출
    response = await client.get("/api/v1/auth/kakao")

    # 3. 검증
    assert response.status_code == 200
    assert response.json() == {"auth_url": mock_auth_url}
    mock_social_auth_service.get_kakao_auth_url.assert_called_once()

    # 4. 의존성 원상복구 (다른 테스트에 영향 주지 않도록)
    app.dependency_overrides.pop(get_social_auth_service, None)


@pytest.mark.asyncio
async def test_kakao_callback_success(client):
    """[API] 카카오 로그인 콜백 성공 테스트 (모킹)"""
    # 1. 의존성 모킹
    mock_social_auth_service = AsyncMock()
    mock_token_response = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_type": "bearer",
    }
    # 콜백 시 토큰을 정상적으로 반환한다고 설정
    mock_social_auth_service.kakao_login.return_value = mock_token_response

    app.dependency_overrides[get_social_auth_service] = lambda: mock_social_auth_service

    # 2. API 호출 (카카오에서 리다이렉트되어 들어오는 상황 가정)
    response = await client.get("/api/v1/auth/kakao/redirect?code=dummy_auth_code&state=dummy_state")

    # 3. 검증
    assert response.status_code == 200
    assert response.json() == mock_token_response

    # 서비스의 kakao_login 메서드가 정확한 파라미터와 함께 호출되었는지 확인
    mock_social_auth_service.kakao_login.assert_called_once_with("dummy_auth_code", "dummy_state")

    # 4. 의존성 원상복구
    app.dependency_overrides.pop(get_social_auth_service, None)
