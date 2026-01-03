from pydantic import BaseModel, EmailStr, constr
from datetime import date

class SignUpRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=20)
    checked_password: constr(min_length=8, max_length=20)
    nickname: constr(min_length=2, max_length=20)
    name: constr(min_length=2, max_length=20)
    birth: date
    phone_num: constr(min_length=10, max_length=11)


class SignUpResponse(BaseModel):
    email: str
    message: str = "회원가입이 완료되었습니다."

    class Config:
        from_attributes = True

class LogInRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=20)

class LogInResponse(BaseModel):
    access_token: str