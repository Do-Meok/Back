from fastapi import APIRouter, Depends,status

from api.v1.deps import get_auth_service
from core.exception.exceptions import UnAuthorizedException, InvalidTokenException
from core.exception.openapi import create_error_response

from domains.auth.schemas import LogInRequest, RefreshTokenRequest, LogInResponse
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
    request: LogOutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await auth_service.log_out(request.refresh_token)
    return {"message": "로그아웃 되었습니다."}

"""
@router.get("/kakao", status_code=200, summary="카카오 로그인 URL 반환", response_model=KaKaoAuthUrlResponse)
async def get_kakao_url(
    social_auth_service: SocialAuthService = Depends(get_social_auth_service),
):
    auth_url = await social_auth_service.get_kakao_auth_url()
    return {"auth_url": auth_url}


@router.get(
    "/kakao/redirect",
    status_code=200,
    summary="카카오 로그인 콜백",
    responses=create_error_response(OAuthStateMismatchException),
)
async def kakao_callback(
    code: str, state: str, social_auth_service: SocialAuthService = Depends(get_social_auth_service)
):
    return await social_auth_service.kakao_login(code, state)
"""