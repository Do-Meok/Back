from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, EmailStr, Field, model_validator

from domains.user.schemas import UserInfoResponse


# Request
class LogInRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., description="비밀번호", min_length=8, max_length=20)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="리프레시 토큰")


class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="로그인 ID로 사용될 메일", examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=20, description="비밀번호 (8~20자)")
    checked_password: str = Field(..., min_length=8, max_length=20, description="비밀번호 확인")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임 (2~20자)")

    name: str = Field(..., min_length=2, max_length=20, description="사용자 이름", examples=["홍길동"])
    birth: date = Field(..., description="사용자 생년월일", examples=[date(1900, 1, 1), date(2000, 1, 1)])
    phone_num: str = Field(..., min_length=12, max_length=13, description="사용자 전화번호", examples=["010-1234-5678"])


class EmailVerifyRequest(BaseModel):
    email: EmailStr = Field(..., description="인증할 이메일")
    code: str = Field(..., min_length=6, max_length=6, description="6자리 인증 코드")


class EmailResendRequest(BaseModel):
    email: EmailStr = Field(..., description="인증 코드를 재발송할 이메일")


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="비밀번호를 재설정할 이메일")


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr = Field(..., description="비밀번호를 재설정할 이메일")
    code: str = Field(..., min_length=6, max_length=6, description="6자리 인증 코드")
    new_password: str = Field(..., min_length=8, max_length=20, description="새 비밀번호")
    checked_new_password: str = Field(..., min_length=8, max_length=20, description="새 비밀번호 확인")

    @model_validator(mode="after")
    def verify_password_match(self) -> Self:
        if self.new_password != self.checked_new_password:
            raise ValueError("비밀번호 확인이 일치하지 않습니다.")
        return self


# Response
class LogInResponse(BaseModel):
    info: UserInfoResponse
    access_token: str = Field(..., description="인증을 위한 액세스 토큰")
    refresh_token: str = Field(..., description="액세스 토큰 갱신용 리프레시 토큰")


class SignupAcceptedResponse(BaseModel):
    email: EmailStr
    message: str
    expires_in_seconds: int
    quota_remaining: int = Field(description="오늘 이 이메일로 남은 인증메일 발송 가능 횟수")


class PasswordResetAcceptedResponse(BaseModel):
    message: str
    quota_remaining: int = Field(description="오늘 이 이메일로 남은 인증메일 발송 가능 횟수")


class KakaoLoginRequest(BaseModel):
    access_token: str = Field(..., description="카카오 액세스 토큰")


class KakaoWebLoginRequest(BaseModel):
    code: str = Field(..., description="카카오 인가 코드")
    redirect_uri: str = Field(..., description="인가 코드 요청 시 사용한 리다이렉트 URI")


class KakaoCompleteRequest(BaseModel):
    signup_token: str = Field(..., description="카카오 가입용 임시 토큰")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임")
    email: EmailStr = Field(..., description="이메일")

    name: str = Field(..., min_length=2, max_length=20, description="사용자 이름", examples=["홍길동"])
    birth: date = Field(..., description="사용자 생년월일", examples=[date(1900, 1, 1), date(2000, 1, 1)])
    phone_num: str = Field(..., min_length=12, max_length=13, description="사용자 전화번호", examples=["010-1234-5678"])


class KakaoAuthResponse(BaseModel):
    status: Literal["authenticated"] = "authenticated"
    info: UserInfoResponse = Field(..., description="사용자 정보")
    access_token: str = Field(..., description="인증을 위한 액세스 토큰")
    refresh_token: str = Field(..., description="액세스 토큰 갱신용 리프레시 토큰")


class KakaoNeedsProfileResponse(BaseModel):
    status: Literal["needs_profile"] = "needs_profile"
    signup_token: str = Field(..., description="추가 정보 입력 시 사용할 카카오 가입용 임시 토큰")
