from fastapi import APIRouter, Depends, status

from api.deps import get_auth_service
from core.exception.exceptions import (
    BadRequestException,
    ConflictException,
    InvalidTokenException,
    UnAuthorizedException,
    UserNotFoundException,
)
from core.exception.openapi import create_error_response
from domains.auth.schemas import (
    EmailResendRequest,
    EmailVerifyRequest,
    KakaoAuthResponse,
    KakaoCompleteRequest,
    KakaoLoginRequest,
    KakaoNeedsProfileResponse,
    LogInRequest,
    LogInResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    SignupAcceptedResponse,
    SignUpRequest,
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


@router.post(
    "/signup/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="회원가입 요청",
    description="가입 정보를 임시 저장하고 이메일로 인증 코드를 발송합니다. 계정은 인증 완료 시 생성됩니다.",
    response_model=SignupAcceptedResponse,
    responses=create_error_response(ConflictException, BadRequestException),
)
async def signup_request(
    request: SignUpRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SignupAcceptedResponse:
    return await auth_service.signup(request)


@router.post(
    "/signup/verify",
    status_code=status.HTTP_200_OK,
    summary="회원가입 이메일 인증",
    description="인증 코드를 검증하고 계정을 생성한 뒤 로그인 토큰을 발급합니다.",
    response_model=LogInResponse,
    responses=create_error_response(BadRequestException, UserNotFoundException),
)
async def signup_verify(
    request: EmailVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogInResponse:
    return await auth_service.verify_email(request)


@router.post(
    "/signup/resend",
    status_code=status.HTTP_202_ACCEPTED,
    summary="회원가입 인증 코드 재발송",
    response_model=SignupAcceptedResponse,
    responses=create_error_response(BadRequestException, UserNotFoundException),
)
async def signup_resend(
    request: EmailResendRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SignupAcceptedResponse:
    return await auth_service.resend_verification(request)


@router.post(
    "/password/reset/request",
    status_code=status.HTTP_200_OK,
    summary="비밀번호 재설정 요청",
    description="가입된 이메일이면 인증 코드를 발송합니다. 이메일 존재 여부와 무관하게 항상 동일하게 응답합니다.",
)
async def password_reset_request(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    return await auth_service.request_password_reset(request)


@router.post(
    "/password/reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="비밀번호 재설정 확인",
    description="인증 코드를 검증하고 새 비밀번호로 변경합니다. 기존 로그인 세션은 모두 무효화됩니다.",
    responses=create_error_response(BadRequestException),
)
async def password_reset_confirm(
    request: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    return await auth_service.confirm_password_reset(request)
