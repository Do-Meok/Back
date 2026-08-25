from typing import Literal
from pydantic import BaseModel, EmailStr, constr, Field

from domains.user.schemas import UserInfoResponse


# Request
class LogInRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=20)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="리프레시 토큰")


# Response
class LogInResponse(BaseModel):
    info: UserInfoResponse
    access_token: str = Field(..., description="인증을 위한 액세스 토큰")
    refresh_token: str = Field(..., description="액세스 토큰 갱신용 리프레시 토큰")
