from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from domains.user.model import User


class UserInfoResponse(BaseModel):
    email: EmailStr = Field(..., description="이메일")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임")

    name: str | None = Field(None, description="사용자 실명")
    birth: date | None = Field(None, description="생년월일")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_user(cls, user: User, phone_num: str | None = None) -> Self:
        return cls(
            email=user.email,
            nickname=user.nickname,
            name=user.name,
            birth=user.birth,
        )


class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="로그인 ID로 사용될 메일", examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=20, description="비밀번호 (8~20자)")
    checked_password: str = Field(..., min_length=8, max_length=20, description="비밀번호 확인")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임 (2~20자)")

    name: str | None = Field(None, min_length=2, max_length=20, description="사용자 이름 (필수X)", examples=["홍길동"])
    birth: date | None = Field(
        None, description="사용자 생년월일 (필수X)", examples=[date(1900, 1, 1), date(2000, 1, 1)]
    )
    phone_num: str | None = Field(
        None, min_length=10, max_length=11, description="사용자 전화번호 (필수X)", examples=["010-1234-5678"]
    )


class SignUpResponse(BaseModel):
    info: UserInfoResponse
    access_token: str
    refresh_token: str


class UpdateUserRequest(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임 변경 (2~20자)")


class UpdatePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=20)
    new_password: str = Field(..., min_length=8, max_length=20)
    checked_new_password: str = Field(..., min_length=8, max_length=20)

    @model_validator(mode="after")
    def verify_password_match(self):
        if self.new_password != self.checked_new_password:
            raise ValueError("비밀번호 확인이 일치하지 않습니다.")
        return self
