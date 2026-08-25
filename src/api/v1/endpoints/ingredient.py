from fastapi import APIRouter, Depends, status

from api.v1.deps import get_ingredient_service
from core.exception.exceptions import IngredientNotFoundException, UnAuthorizedException
from core.exception.openapi import create_error_response

from domains.ingredient.schemas import (
    AddIngredientRequest,
    AddIngredientResponse,
    GetIngredientResponse,
)
from domains.ingredient.service import IngredientService

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="식재료 추가",
    response_model=list[AddIngredientResponse],
    responses=create_error_response(UnAuthorizedException),
)
async def add_ingredients(
    request: AddIngredientRequest,
    service: IngredientService = Depends(get_ingredient_service),
) -> list[AddIngredientResponse]:
    return await service.add_ingredients(request)


@router.get(
    "",
    summary="식재료 조회 API",
    status_code=status.HTTP_200_OK,
    response_model=list[GetIngredientResponse],
    responses=create_error_response(UnAuthorizedException),
)
async def get_list_ingredients(
    service: IngredientService = Depends(get_ingredient_service),
) -> list[GetIngredientResponse]:
    return await service.get_ingredients()


@router.delete(
    "/{ingredient_id}",
    summary="식재료 삭제",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=create_error_response(UnAuthorizedException, IngredientNotFoundException),
)
async def delete_ingredient(
    ingredient_id: int,
    ingredient_service: IngredientService = Depends(get_ingredient_service),
) -> None:
    await ingredient_service.delete_ingredient(ingredient_id)

@router.get(
    "/all-delete",
    summary="식재료 일괄 삭제",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=create_error_response(
        UnAuthorizedException,
        IngredientNotFoundException,
    )
)
async def delete_all_ingredient(
    service: IngredientService = Depends(get_ingredient_service),
) -> None:
    await service.delete_all_ingredients()