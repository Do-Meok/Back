from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from core.di import get_user_service, get_current_user, get_social_auth_service
from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    DuplicatePhoneNumException,
    InvalidCheckedPasswordException,
    InvalidCredentialsException,
    UserNotFoundException,
    IncorrectPasswordException,
    PasswordUnchangedException,
    PasswordMismatchException,
)
from domains.user.schemas import (
    SignUpRequest,
    SignUpResponse,
    LogInRequest,
    LogInResponse,
    InfoResponse,
    RefreshTokenRequest,
    LogOutRequest,
    FindEmailRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ChangeNicknameRequest,
)
from domains.user.service import UserService, SocialAuthService
from util.docs import create_error_response

router = APIRouter()


@router.post(
    "/sign-up",
    status_code=201,
    summary="회원가입 API",
    response_model=SignUpResponse,
    responses=create_error_response(
        DuplicateEmailException,
        DuplicateNicknameException,
        DuplicatePhoneNumException,
        InvalidCheckedPasswordException,
    ),
)
async def user_sign_up(request: SignUpRequest, user_service: UserService = Depends(get_user_service)):
    user = await user_service.sign_up(request)
    return SignUpResponse(email=user.email)


@router.post(
    "/log-in",
    status_code=200,
    summary="로그인 API",
    response_model=LogInResponse,
    responses=create_error_response(
        InvalidCredentialsException,
    ),
)
async def user_log_in(
    request: LogInRequest,
    req: Request,
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.log_in(request, req)


@router.post(
    "/refresh",
    status_code=200,
    summary="토큰 재발급 API",
    response_model=LogInResponse,
)
async def refresh_token(
    request: RefreshTokenRequest,
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.refresh_token(request)


@router.get(
    "/info",
    status_code=200,
    summary="유저 정보 호출 API",
    response_model=InfoResponse,
    responses=create_error_response(UserNotFoundException),
)
async def user_info(
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_user_info(current_user.id)


@router.post(
    "/log-out",
    status_code=200,
    summary="로그아웃 API",
)
async def user_log_out(
    request: LogOutRequest,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.log_out(request, current_user.id)
    return {"message": "로그아웃 되었습니다."}


@router.post(
    "/find-email",
    status_code=200,
    summary="아이디 찾기 API",
)
async def find_email(
    request: FindEmailRequest,
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.find_email(request)


@router.patch(
    "/change-pw",
    status_code=200,
    summary="비밀번호 변경 API (로그인 상태)",
    responses=create_error_response(
        IncorrectPasswordException,
        PasswordUnchangedException,
        PasswordMismatchException,
    ),
)
async def change_pw(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.change_password(request, current_user.id)
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


@router.post(
    "/reset-pw",
    status_code=200,
    summary="비밀번호 재설정 API (비밀번호 찾기)",
)
async def reset_pw(
    request: ResetPasswordRequest,
    user_service: UserService = Depends(get_user_service),
):
    await user_service.reset_password(request)
    return {"message": "비밀번호가 재설정되었습니다. 새 비밀번호로 로그인해주세요."}


@router.patch(
    "/nickname",
    status_code=200,
    summary="닉네임 변경 API",
    responses=create_error_response(DuplicateNicknameException),
)
async def change_nickname(
    request: ChangeNicknameRequest,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.change_nickname(request, current_user.id)

    return {"message": "닉네임이 변경되었습니다.", "nickname": request.nickname}


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
