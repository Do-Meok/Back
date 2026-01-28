from fastapi import APIRouter, Depends

from core.di import get_ingredient_service
from domains.ingredient.exceptions import (
    IngredientNotFoundException,
    ValueNotFoundException,
)
from domains.ingredient.schemas import (
    AddIngredientRequest,
    AddIngredientResponse,
    SetIngredientRequest,
    StorageType,
    UpdateIngredientRequest,
    GetIngredientResponse,
    BulkMoveIngredientRequest,
    BulkMoveResponse,
)
from domains.ingredient.service import IngredientService
from util.docs import create_error_response

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


@router.patch(
    "/{ingredient_id}",
    summary="식재료 유통기한 및 보관장소 설정 API",
    status_code=200,
    response_model=GetIngredientResponse,
    responses=create_error_response(ValueNotFoundException),
)
async def set_ingredient_details(
    ingredient_id: int,
    request: SetIngredientRequest,
    service: IngredientService = Depends(get_ingredient_service),
):
    """
    ## 이거는 초기에 설정하는 것이기에, 보관장소와 유통기한을 반드시 둘 다 입력해야함
    """
    return await service.set_expiration_and_storage(ingredient_id, request)


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
    return await service.get_ingredients(
        storage=storage, is_unclassified=is_unclassified
    )


@router.get(
    "/detail",
    summary="식재료 단일 조회 API",
    status_code=200,
    response_model=GetIngredientResponse,
    responses=create_error_response(IngredientNotFoundException),
)
async def get_ingredient(
    ingredient_id: int, service: IngredientService = Depends(get_ingredient_service)
):
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


@router.patch(
    "/update/{ingredient_id}",
    summary="식재료 수정 API",
    status_code=200,
    response_model=GetIngredientResponse,
    responses=create_error_response(IngredientNotFoundException),
)
async def update_ingredient(
    ingredient_id: int,
    request: UpdateIngredientRequest,
    ingredient_service: IngredientService = Depends(get_ingredient_service),
):
    """
    ## purchase_date, expiration_date, storage_type 중 한개만 설정도 가능, null로 주면 됌.
    ## null로 주면 null대신 기존에 있던 값 그대로 쓰는 것
    """
    return await ingredient_service.update_ingredient(ingredient_id, request)


@router.get(
    "/unassigned",
    summary="냉장고 칸 미분류 식재료 조회 API",
    response_model=list[GetIngredientResponse],
)
async def get_unassigned_ingredients(
    service: IngredientService = Depends(get_ingredient_service),
):
    """
    아직 냉장고 칸에 배정되지 않은(미분류) 식재료 목록을 조회
    """
    return await service.get_unassigned_ingredients()


@router.patch(
    "/{compartment_id}/ingredients",
    summary="미분류된 식재료들 칸 이동 API",
    response_model=BulkMoveResponse,
)
async def move_ingredients_to_compartment(
    compartment_id: int,
    request: BulkMoveIngredientRequest,
    service: IngredientService = Depends(get_ingredient_service),
):
    """
    선택한 미분류 식재료들을 특정 칸(compartment_id)으로 일괄 이동시킴
    ingredient_ids로 옮기고 옮기는 방식은 6,7,11 이런식으로 옮기면 됌
    """
    return await service.move_ingredients(compartment_id, request)
