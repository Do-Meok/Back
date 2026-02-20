from datetime import date

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="사용자 이메일")
    password: str = Field(..., min_length=8, max_length=20)
    checked_password: str = Field(..., min_length=8, max_length=20)
    nickname: str = Field(..., min_length=2, max_length=20)

    name: str | None = Field(None, min_length=2, max_length=20)
    birth: date | None = Field(None)
    phone_num: str | None = Field(None, min_length=10, max_length=11)


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
