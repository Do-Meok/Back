# src/core/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class GlobalErrorResponse(BaseModel):
    status_code: int = Field(..., examples=[400])
    code: str = Field(..., examples=["ERROR_CODE_STRING"])
    detail: str = Field(..., examples=["에러에 대한 상세 메시지입니다."])
    errors: Optional[List[Any]] = Field(
        None, description="유효성 검사 에러 시 상세 내용"
    )
