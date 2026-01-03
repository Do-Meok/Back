from fastapi import APIRouter, Depends, Request

from core.di import get_user_service
from domains.user.schemas import SignUpRequest, SignUpResponse, LogInRequest
from domains.user.service import UserService

router = APIRouter()

@router.post("/sign-up", status_code=201)
async def user_sign_up(
        request: SignUpRequest,
        user_service: UserService = Depends(get_user_service)
):
    user = await user_service.sign_up(request)
    # User 객체의 email을 꺼내서 응답에 넣어줌
    return SignUpResponse(email=user.email)

@router.post("/log-in", status_code=200)
async def user_log_in(
        request: LogInRequest,
        req: Request,
        user_service: UserService = Depends(get_user_service)
):
    return await user_service.log_in(request, req)