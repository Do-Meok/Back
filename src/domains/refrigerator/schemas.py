from pydantic import BaseModel, Field, ConfigDict


class AddRefrigeratorRequest(BaseModel):
    name: str
    pos_x: int = Field(..., ge=1, le=4, description="가로 칸 수(1~4)")
    pos_y: int = Field(..., ge=1, le=3, description="세로 칸 수(1~3)")


class AddRefrigeratorResponse(BaseModel):
    id: int
    name: str
    pos_x: int
    pos_y: int

    model_config = ConfigDict(from_attributes=True)


class CompartmentResponse(BaseModel):
    id: int
    name: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)

class GetRefrigeratorResponse(BaseModel):
    id: int
    name: str
    pos_x: int
    pos_y: int
    compartments: list[CompartmentResponse]

    model_config = ConfigDict(from_attributes=True)