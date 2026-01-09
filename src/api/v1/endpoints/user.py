from fastapi import APIRouter, Depends, Request

from core.di import get_user_service, get_current_user
from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    DuplicatePhoneNumException,
    InvalidCheckedPasswordException,
    InvalidCredentialsException,
    UserNotFoundException,
)
from domains.user.schemas import (
    SignUpRequest,
    SignUpResponse,
    LogInRequest,
    LogInResponse,
    InfoResponse,
)
from domains.user.service import UserService
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
async def user_sign_up(
    request: SignUpRequest, user_service: UserService = Depends(get_user_service)
):
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
