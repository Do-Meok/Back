from fastapi import APIRouter, Depends, status

from api.deps import get_current_user, get_user_service
from core.exception.exceptions import ConflictException, UnAuthorizedException
from core.exception.openapi import create_error_response
from domains.user.model import User
from domains.user.schemas import (
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserInfoResponse,
)
from domains.user.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


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
