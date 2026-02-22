from pydantic import BaseModel


class LogInResponse(BaseModel):
    access_token: str
    refresh_token: str


class KaKaoAuthUrlResponse(BaseModel):
    auth_url: str
