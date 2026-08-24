from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from domains.user.model import User


class SignUpResponse(BaseModel):
    email: EmailStr = Field(..., description="가입된 사용자 이메일", examples=["test@example.com"])
    message: str = Field(default="회원가입이 완료되었습니다.", description="결과 메시지")

    model_config = ConfigDict(from_attributes=True)


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


class FindEmailResponse(BaseModel):
    email: EmailStr = Field(..., description="찾은 이메일 계정", examples=["test@example.com"])

    model_config = ConfigDict(from_attributes=True)
