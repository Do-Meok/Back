from fastapi import APIRouter, Depends
from typing import List

from core.di import get_ingredient_service
from domains.ingredient.schemas import AddIngredientRequest, AddIngredientResponse
from domains.ingredient.service import IngredientService

router = APIRouter()


@router.post("", status_code=201, response_model=List[AddIngredientResponse])
async def add_ingredient(
    request: AddIngredientRequest,
    service: IngredientService = Depends(get_ingredient_service),
):
    return await service.add_ingredient(request)
