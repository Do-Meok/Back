from fastapi import Depends, APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.di import get_auth_service, get_current_user, get_social_auth_service

from domains.auth.schemas import LogInResponse, LogInRequest, RefreshTokenRequest, LogOutRequest
from domains.auth.service import AuthService
from domains.auth.social_service import SocialAuthService

from domains.auth.exceptions import InvalidCredentialsException
from util.docs import create_error_response

router = APIRouter()


@router.post(
    "/log-in",
    status_code=200,
    summary="로그인 API",
    response_model=LogInResponse,
    responses=create_error_response(InvalidCredentialsException),
)
async def user_log_in(
    request: LogInRequest,
    req: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.log_in(request, req)


@router.post(
    "/refresh",
    status_code=200,
    summary="토큰 재발급 API",
    response_model=LogInResponse,
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.refresh_token(request)


@router.post(
    "/log-out",
    status_code=200,
    summary="로그아웃 API",
)
async def user_log_out(
    request: LogOutRequest,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.log_out(request, current_user.id)
    return {"message": "로그아웃 되었습니다."}


@router.get("/kakao", status_code=200, summary="카카오 로그인 URL 반환")
async def get_kakao_url(
    social_auth_service: SocialAuthService = Depends(get_social_auth_service),
):
    auth_url = await social_auth_service.get_kakao_auth_url()
    return JSONResponse({"auth_url": auth_url})


@router.get("/kakao/redirect", status_code=200, summary="카카오 로그인 콜백")
async def kakao_callback(
    code: str, state: str, social_auth_service: SocialAuthService = Depends(get_social_auth_service)
):
    token_response = await social_auth_service.kakao_login(code, state)
    return token_response
