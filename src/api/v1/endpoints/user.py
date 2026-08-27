from fastapi import APIRouter, Depends, status

from api.deps import get_auth_service, get_current_user, get_user_service
from core.exception.exceptions import ConflictException, UnAuthorizedException
from core.exception.openapi import create_error_response
from domains.auth.service import AuthService
from domains.user.model import User
from domains.user.schemas import (
    SignUpRequest,
    SignUpResponse,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserInfoResponse,
)
from domains.user.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sign-up", status_code=status.HTTP_201_CREATED, summary="회원가입 API", response_model=SignUpResponse)
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
    responses=create_error_response(ConflictException),
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
