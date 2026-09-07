from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AddIngredientRequest(BaseModel):
    ingredients: list[str]


class DeleteIngredientsRequest(BaseModel):
    ingredient_ids: list[int] = Field(min_length=1, description="삭제할 식재료 id 목록")


class AddIngredientResponse(BaseModel):
    id: int
    ingredient_name: str
    created_at: date

    model_config = ConfigDict(from_attributes=True)


class GetIngredientResponse(BaseModel):
    id: int
    ingredient_name: str
    created_at: date

    model_config = ConfigDict(from_attributes=True)
