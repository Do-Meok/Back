from pydantic import BaseModel, EmailStr, constr, Field, ConfigDict
from datetime import date
from typing import Optional


class SignUpRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=20)
    checked_password: constr(min_length=8, max_length=20)
    nickname: constr(min_length=2, max_length=20)

    name: Optional[constr(min_length=2, max_length=20)] = None
    birth: Optional[date] = None
    phone_num: Optional[constr(min_length=10, max_length=11)] = None


class SignUpResponse(BaseModel):
    email: str = Field(..., examples=["test@example.com"])
    message: str = Field(
        default="회원가입이 완료되었습니다.", examples=["회원가입이 완료되었습니다."]
    )

    model_config = ConfigDict(from_attributes=True)


class LogInRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=20)


class LogInResponse(BaseModel):
    access_token: str
