from fastapi import APIRouter, Depends, status

from api.deps import get_current_user, get_user_service, get_auth_service
from core.exception.exceptions import ConflictException, UnAuthorizedException
from core.exception.openapi import create_error_response
from domains.auth.service import AuthService
from domains.user.schemas import SignUpRequest, SignUpResponse, UserInfoResponse, UpdateUserRequest, \
    UpdatePasswordRequest
from domains.user.service import UserService
from domains.user.model import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/sign-up",
    status_code=status.HTTP_201_CREATED,
    summary="회원가입 API",
    response_model=SignUpResponse
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
    "/me",
    status_code=status.HTTP_200_OK,
    summary="유저 정보 반환 API",
    response_model=UserInfoResponse,
    description="현재 로그인한 사용자의 프로필 정보를 반환",
)
async def user_info(user: User = Depends(get_current_user)) -> UserInfoResponse:
    return UserInfoResponse.from_user(user)

@router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="유저 정보 변경(닉네임)",
    responses = create_error_response(ConflictException),
)

async def update_me(
        request: UpdateUserRequest,
        user: User = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service),
) -> UserInfoResponse:
    return await user_service.update_user(user, request)

@router.patch(
    "/me/password",
    response_model=UserInfoResponse,
    summary="비밀번호 변경",
    description="현재 비밀번호 확인 후 새 비밀번호로 변경",
    responses=create_error_response(UnAuthorizedException),
)
async def update_password(
    request: UpdatePasswordRequest,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserInfoResponse:
    return await user_service.update_password(user, request)

"""
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

"""