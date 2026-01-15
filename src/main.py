from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.v1.api import api_router
from core.exception.exceptions import BaseCustomException
from core.exception.exception_handlers import (
    custom_exception_handler,
    system_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

app = FastAPI()

app.add_exception_handler(BaseCustomException, custom_exception_handler)
app.add_exception_handler(Exception, system_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}
