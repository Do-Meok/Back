"""
소셜 로그인 연동을 위한 kakao_client
"""

import httpx

from core.config import settings
from core.exception.exceptions import BadRequestException, ExternalServiceException

KAKAO_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"


async def exchange_code_for_token(code: str, redirect_uri: str) -> str:
    """
    웹 카카오 로그인(Authorization Code) 플로우에서 받은 인가 코드를 access_token으로 교환함
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_REST_API_KEY.get_secret_value() if settings.KAKAO_REST_API_KEY else "",
        "redirect_uri": redirect_uri,
        "code": code,
    }
    if settings.KAKAO_CLIENT_SECRET:
        data["client_secret"] = settings.KAKAO_CLIENT_SECRET.get_secret_value()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                KAKAO_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise ExternalServiceException(detail="카카오 인증 서버와 통신에 실패했습니다.") from exc

    if response.status_code != httpx.codes.OK:
        raise BadRequestException(detail="카카오 인가 코드가 유효하지 않습니다.")

    access_token = response.json().get("access_token")
    if not access_token:
        raise BadRequestException(detail="카카오 인가 코드가 유효하지 않습니다.")
    return str(access_token)


async def fetch_kakao_user_id(access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(KAKAO_USER_ME_URL, headers=headers)
    except httpx.HTTPError as exc:
        raise ExternalServiceException(detail="카카오 인증 서버와 통신에 실패했습니다.") from exc

    if response.status_code == 401:
        raise BadRequestException(detail="카카오 인증 실패")
    if response.status_code != httpx.codes.OK:
        raise ExternalServiceException(detail="카카오 사용자 정보를 가져오지 못했습니다.")

    data = response.json()
    kakao_id = data.get("id")
    if kakao_id is None:
        raise BadRequestException(detail="카카오 인증 실패")
    return str(kakao_id)
