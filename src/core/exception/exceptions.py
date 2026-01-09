# src/core/exceptions.py
from pydantic import BaseModel, Field
from typing import Any


class BaseCustomException(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        self.status_code = status_code
        self.code = code
        self.detail = detail
        super().__init__(detail)


class DatabaseException(BaseCustomException):
    def __init__(self, detail: str = "데이터베이스 에러"):
        super().__init__(status_code=500, code="DB_ERROR", detail=detail)


class UnexpectedException(BaseCustomException):
    def __init__(self, detail: str = "서버 내부 오류"):
        super().__init__(status_code=500, code="SERVER_ERROR", detail=detail)


class GlobalErrorResponse(BaseModel):
    status_code: int = Field(..., examples=[400])
    code: str = Field(..., examples=["ERROR_CODE_STRING"])
    detail: str = Field(..., examples=["에러에 대한 상세 메시지입니다."])
    errors: list[Any] | None = Field(None, description="유효성 검사 에러 시 상세 내용")
