from pydantic import BaseModel, Field


class OcrReceiptResponse(BaseModel):
    ingredients: list[str] = Field(default_factory=list)


class _LLMIngredientsPayload(BaseModel):
    ingredients: list[str] = Field(default_factory=list)
