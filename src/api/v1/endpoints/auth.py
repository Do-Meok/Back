from fastapi import APIRouter, Depends, status

from api.deps import get_auth_service
from core.exception.exceptions import InvalidTokenException, UnAuthorizedException
from core.exception.openapi import create_error_response
from domains.auth.schemas import (
    KakaoAuthResponse,
    KakaoCompleteRequest,
    KakaoLoginRequest,
    KakaoNeedsProfileResponse,
    LogInRequest,
    LogInResponse,
    RefreshTokenRequest,
)
from domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/log-in",
    status_code=status.HTTP_200_OK,
    summary="로그인",
    response_model=LogInResponse,
    responses=create_error_response(UnAuthorizedException),
)
async def user_log_in(
    request: LogInRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogInResponse:
    return await auth_service.log_in(request)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="토큰 갱신",
    description="리프레시 토큰으로 액세스·리프레시 토큰을 재발급",
    response_model=LogInResponse,
    responses=create_error_response(InvalidTokenException),
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogInResponse:
    return await auth_service.refresh(request.refresh_token)


@router.post(
    "/log-out",
    status_code=status.HTTP_200_OK,
    summary="로그아웃",
    description="리프레시 토큰을 무효화하여 로그아웃함",
)
async def user_log_out(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await auth_service.log_out(request.refresh_token)
    return {"message": "로그아웃 되었습니다."}


@router.post(
    "/kakao",
    status_code=status.HTTP_200_OK,
    response_model=KakaoAuthResponse | KakaoNeedsProfileResponse,
)
async def kakao_login(
    request: KakaoLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> KakaoAuthResponse | KakaoNeedsProfileResponse:
    return await auth_service.login_with_kakao(request.access_token)


@router.post(
    "/kakao/complete",
    status_code=status.HTTP_200_OK,
    response_model=KakaoAuthResponse,
)
async def kakao_complete(
    request: KakaoCompleteRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> KakaoAuthResponse:
    return await auth_service.complete_kakao_signup(request)
