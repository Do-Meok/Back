from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignUpResponse(BaseModel):
    email: EmailStr = Field(..., description="가입된 사용자 이메일", examples=["test@example.com"])
    message: str = Field(default="회원가입이 완료되었습니다.", description="결과 메시지")

    model_config = ConfigDict(from_attributes=True)


class InfoResponse(BaseModel):
    email: EmailStr = Field(..., description="이메일")
    nickname: str = Field(..., min_length=2, max_length=20, description="닉네임")

    name: str | None = Field(None, description="사용자 실명")
    birth: date | None = Field(None, description="생년월일")
    phone_num: str | None = Field(None, description="복호화된 전화번호")

    model_config = ConfigDict(from_attributes=True)


class FindEmailResponse(BaseModel):
    email: EmailStr = Field(..., description="찾은 이메일 계정", examples=["test@example.com"])

    model_config = ConfigDict(from_attributes=True)
