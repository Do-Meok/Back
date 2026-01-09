from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date
from enum import Enum


class StorageType(str, Enum):
    FRIDGE = "FRIDGE"
    FREEZER = "FREEZER"
    ROOM = "ROOM"


# --- Request ---
class AddIngredientRequest(BaseModel):
    # 유통기한 안넣을 시 Default -> Today
    purchase_date: date = Field(default_factory=date.today)
    ingredients: list[str]

    @field_validator("purchase_date", mode="before")
    @classmethod
    def set_today_if_null(cls, v):
        if v is None:
            return date.today()
        return v


class SetIngredientRequest(BaseModel):
    expiration_date: date | None = None
    storage_type: StorageType | None = None


class UpdateIngredientRequest(BaseModel):
    purchase_date: date | None = None
    expiration_date: date | None = None
    storage_type: StorageType | None = None


# --- Response ---


class AddIngredientResponse(BaseModel):
    id: int
    ingredient_name: str
    purchase_date: date

    model_config = ConfigDict(from_attributes=True)


class GetIngredientResponse(BaseModel):
    id: int
    ingredient_name: str
    purchase_date: date
    expiration_date: date | None = None
    storage_type: StorageType | None = None
