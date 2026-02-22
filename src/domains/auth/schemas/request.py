from pydantic import BaseModel, EmailStr, constr


class LogInRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=20)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogOutRequest(BaseModel):
    refresh_token: str
