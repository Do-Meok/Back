from datetime import date
from typing import Self

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from domains.user.model import User


class UserInfoResponse(BaseModel):
    email: EmailStr = Field(..., description="이메일")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임")

    name: str | None = Field(None, description="사용자 실명")
    birth: date | None = Field(None, description="생년월일")
    phone_num: str | None = Field(None, description="복호화된 전화번호")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_user(cls, user: User, phone_num: str | None = None) -> Self:
        return cls (
            email=user.email,
            nickname=user.nickname,
            name=user.name,
            birth=user.birth,
            phone_num=phone_num
        )

class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="로그인 ID로 사용될 메일", examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=20, description="비밀번호 (8~20자)")
    checked_password: str = Field(..., min_length=8, max_length=20, description="비밀번호 확인")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임 (2~20자)")

    name: str | None = Field(None, min_length=2, max_length=20, description="사용자 이름 (필수X)", examples=["홍길동"])
    birth: date | None = Field(None, description="사용자 생년월일 (필수X)", examples=[date(1900, 1, 1), date(2000, 1, 1)])
    phone_num: str | None = Field(None, min_length=10, max_length=11, description="사용자 전화번호 (필수X)", examples=["010-1234-5678"])

class SignUpResponse(BaseModel):
    info: UserInfoResponse
    access_token: str
    refresh_token: str

"""
class FindEmailRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=20)
    birth: date | None = Field(None)
    phone_num: str | None = Field(None, min_length=10, max_length=11)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=20)
    new_password: str = Field(..., min_length=8, max_length=20)
    checked_new_password: str = Field(..., min_length=8, max_length=20)


class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="사용자 이메일")
    name: str | None = Field(None, min_length=2, max_length=20)
    birth: date | None = Field(None)
    phone_num: str | None = Field(None, min_length=10, max_length=11)
    new_password: str = Field(..., min_length=8, max_length=20)
    checked_new_password: str = Field(..., min_length=8, max_length=20)


class ChangeNicknameRequest(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=20)


class FindEmailResponse(BaseModel):
    email: EmailStr = Field(..., description="찾은 이메일 계정", examples=["test@example.com"])

    model_config = ConfigDict(from_attributes=True)

"""