from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from domains.user.schemas import UserInfoResponse


# Request
class LogInRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., description="비밀번호", min_length=8, max_length=20)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="리프레시 토큰")


# Response
class LogInResponse(BaseModel):
    info: UserInfoResponse
    access_token: str = Field(..., description="인증을 위한 액세스 토큰")
    refresh_token: str = Field(..., description="액세스 토큰 갱신용 리프레시 토큰")


class KakaoLoginRequest(BaseModel):
    access_token: str = Field(..., description="카카오 액세스 토큰")


class KakaoCompleteRequest(BaseModel):
    signup_token: str = Field(..., description="카카오 가입용 임시 토큰")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임")
    email: EmailStr = Field(..., description="이메일")

    name: str = Field(..., min_length=2, max_length=20, description="사용자 이름", examples=["홍길동"])
    birth: date = Field(
        ..., description="사용자 생년월일", examples=[date(1900, 1, 1), date(2000, 1, 1)]
    )
    phone_num: str = Field(
        ..., min_length=12, max_length=13, description="사용자 전화번호", examples=["010-1234-5678"]
    )


class KakaoAuthResponse(BaseModel):
    status: Literal["authenticated"] = "authenticated"
    info: UserInfoResponse
    access_token: str
    refresh_token: str


class KakaoNeedsProfileResponse(BaseModel):
    status: Literal["needs_profile"] = "needs_profile"
    signup_token: str
