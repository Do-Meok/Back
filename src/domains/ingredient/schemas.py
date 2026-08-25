from datetime import date
from pydantic import BaseModel, ConfigDict, Field

class AddIngredientRequest(BaseModel):
    ingredients: list[str]

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