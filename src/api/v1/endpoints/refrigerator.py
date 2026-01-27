from fastapi import APIRouter, Depends

from core.di import get_refrigerator_service, get_ingredient_service
from domains.ingredient.schemas import GetIngredientResponse
from domains.ingredient.service import IngredientService
from domains.refrigerator.schemas import (
    AddRefrigeratorRequest,
    GetRefrigeratorResponse,
    AddRefrigeratorResponse,
)
from domains.refrigerator.service import RefrigeratorService

router = APIRouter()


@router.post(
    "",
    status_code=201,
    summary="냉장고 추가 API",
    response_model=AddRefrigeratorResponse,
)
async def add_refrigerator(
    request: AddRefrigeratorRequest,
    service: RefrigeratorService = Depends(get_refrigerator_service),
):
    return await service.add_refrigerator(request)


@router.get(
    "/{refrigerator_id}",
    summary="냉장고 조회 API",
    response_model=GetRefrigeratorResponse,
)
async def get_refrigerator(
    refrigerator_id: int,
    service: RefrigeratorService = Depends(get_refrigerator_service),
):
    """
    냉장고의 id를 입력하면 pos_x와 pos_y를 기반으로 냉장고의 이미지를 사각형으로 나타내고,
    compartments를 통해 냉장고 칸 시각화함
    """
    return await service.get_refrigerator(refrigerator_id)


@router.get(
    "/{compartment_id}/ingredients",
    summary="냉장고 칸 속 재료 조회 API",
    response_model=list[GetIngredientResponse],
)
async def get_ingredients_by_compartment(
    compartment_id: int,
    service: IngredientService = Depends(get_ingredient_service),
):
    """
    냉장고의 칸 id를 입력하면, 어떤 식재료가 있는지 알려줌
    """
    return await service.get_ingredients_in_compartment(compartment_id)
