from pydantic import BaseModel

class AddItemRequest(BaseModel):
    item_name: str

class AddItemResponse(BaseModel):
    id: int
    item_name: str

class GetItemResponse(BaseModel):
    id: int
    item_name: str