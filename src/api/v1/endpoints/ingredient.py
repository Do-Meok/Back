from fastapi import APIRouter, Depends

from api.v1.deps import get_ingredient_service
from core.exception.openapi import create_error_response
from domains.ingredient.exceptions import (
    IngredientNotFoundException,
)
from domains.ingredient.schemas import (
    AddIngredientRequest,
    AddIngredientResponse,
    GetIngredientResponse,
    StorageType,
)
from domains.ingredient.service import IngredientService

router = APIRouter()


@router.post(
    "",
    status_code=201,
    summary="식재료 추가 API",
    response_model=list[AddIngredientResponse],
)
async def add_ingredient(
    request: AddIngredientRequest,
    service: IngredientService = Depends(get_ingredient_service),
):
    return await service.add_ingredient(request)


@router.get(
    "",
    summary="식재료 조회 API",
    status_code=200,
    response_model=list[GetIngredientResponse],
)
async def get_ingredients(
    is_unclassified: bool | None = None,
    storage: StorageType | None = None,
    service: IngredientService = Depends(get_ingredient_service),
):
    """
    # is_unclassified -> true: 보관 데이터 입력 안된애들 출력
    # storage -> 보관 장소에 따른 데이터 출력(is_unclassified=false와 같이 나와야함)
    ---
    # 3가지 조회를 1개의 API에 묶음
    ## 1) 보관 데이터가 없는 식재료 -> is_unclassified=true
    ## 2) 보관 데이터가 있는 식재료(냉장, 냉동, 실온) -> is_unclassified=false & storage=StorageType
    ## 3) 보관 데이터가 있든 없든 모든 식재료 -> default(아무값도 없이)
    """
    return await service.get_ingredients(storage=storage, is_unclassified=is_unclassified)


@router.get(
    "/detail",
    summary="식재료 단일 조회 API",
    status_code=200,
    response_model=GetIngredientResponse,
    responses=create_error_response(IngredientNotFoundException),
)
async def get_ingredient(ingredient_id: int, service: IngredientService = Depends(get_ingredient_service)):
    return await service.get_ingredient(ingredient_id)


@router.delete(
    "",
    summary="식재료 삭제 API",
    status_code=204,
    responses=create_error_response(IngredientNotFoundException),
)
async def delete_ingredient(
    ingredient_id: int,
    ingredient_service: IngredientService = Depends(get_ingredient_service),
):
    await ingredient_service.delete_ingredient(ingredient_id)
