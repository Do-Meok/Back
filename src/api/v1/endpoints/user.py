from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    DuplicatePhoneNumException,
    IncorrectPasswordException,
    InvalidCheckedPasswordException,
    PasswordMismatchException,
    PasswordUnchangedException,
    UserNotFoundException,
)
from fastapi import APIRouter, Depends, status

from api.v1.deps import get_current_user, get_user_service, get_auth_service
from core.exception.openapi import create_error_response
from domains.auth.service import AuthService
from domains.user.schemas.request import (
    ChangeNicknameRequest,
    ChangePasswordRequest,
    FindEmailRequest,
    ResetPasswordRequest,
    SignUpRequest,
)
from domains.user.schemas.response import FindEmailResponse, UserInfoResponse, SignUpResponse
from domains.user.service import UserService

router = APIRouter()


@router.post(
    "/sign-up",
    status_code=status.HTTP_201_CREATED,
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
        request: SignUpRequest,
        user_service: UserService = Depends(get_user_service),
        auth_service: AuthService = Depends(get_auth_service),
) -> SignUpResponse:
    user = await user_service.sign_up(request)
    tokens = await auth_service.issue_tokens(user)
    return SignUpResponse(
        info=UserInfoResponse.from_user(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.get(
    "/info",
    status_code=200,
    summary="유저 정보 호출 API",
    response_model=UserInfoResponse,
    responses=create_error_response(UserNotFoundException),
)
async def user_info(
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_user_info(current_user.id)


@router.post(
    "/find-email",
    status_code=200,
    summary="아이디 찾기 API",
    response_model=FindEmailResponse,
    responses=create_error_response(UserNotFoundException),
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
        UserNotFoundException,
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
    responses=create_error_response(UserNotFoundException, PasswordMismatchException, PasswordUnchangedException),
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
    responses=create_error_response(UserNotFoundException, DuplicateNicknameException),
)
async def change_nickname(
    request: ChangeNicknameRequest,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.change_nickname(request, current_user.id)
    return {"message": "닉네임이 변경되었습니다.", "nickname": request.nickname}
