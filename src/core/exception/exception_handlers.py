from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exception.exceptions import BaseCustomException


async def custom_exception_handler(request: Request, exc: BaseCustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "code": exc.code,
            "detail": exc.detail,
        },
    )


async def system_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "code": "INTERNAL_SERVER_ERROR",
            "detail": "서버 내부 오류가 발생했습니다. 관리자에게 문의하세요.",
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "code": "HTTP_ERROR",
            "detail": exc.detail,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()

    for error in errors:
        if "ctx" in error:
            for key, value in error["ctx"].items():
                if isinstance(value, Exception):
                    error["ctx"][key] = str(value)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": errors, "message": "유효성 검사 실패"}),
    )
