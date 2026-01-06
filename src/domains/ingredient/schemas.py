from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date
from typing import List


class AddIngredientRequest(BaseModel):
    # 유통기한 안넣을 시 Default -> Today
    purchase_date: date = Field(default_factory=date.today)
    ingredients: List[str]

    @field_validator("purchase_date", mode="before")
    @classmethod
    def set_today_if_null(cls, v):
        if v is None:
            return date.today()
        return v


class AddIngredientResponse(BaseModel):
    id: int
    ingredient_name: str
    purchase_date: date

    model_config = ConfigDict(from_attributes=True)
