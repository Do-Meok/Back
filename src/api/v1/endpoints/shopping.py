from fastapi import APIRouter, Depends

from core.di import get_shopping_service
from domains.shopping.exception import ItemNotFoundException
from domains.shopping.schemas import AddItemRequest, AddItemResponse, GetItemResponse
from domains.shopping.service import ShoppingService
from util.docs import create_error_response

router = APIRouter()


@router.post("", status_code=201, summary="장보기 리스트 추가", response_model=AddItemResponse)
async def add_item(
    request: AddItemRequest,
    service: ShoppingService = Depends(get_shopping_service),
):
    return await service.add_item(request)


@router.get(
    "",
    status_code=200,
    summary="장보기 리스트 조회",
    response_model=list[GetItemResponse],
)
async def get_list(
    service: ShoppingService = Depends(get_shopping_service),
):
    return await service.get_list()


@router.patch(
    "/{shopping_id}",
    status_code=200,
    summary="장보기 상태 변경 (토글)",
    response_model=GetItemResponse,
    responses=create_error_response(ItemNotFoundException),
)
async def change_status(
    shopping_id: int,
    service: ShoppingService = Depends(get_shopping_service),
):
    return await service.toggle_item(shopping_id)


@router.delete(
    "/{shopping_id}",
    status_code=204,
    summary="장보기 리스트 삭제",
    responses=create_error_response(ItemNotFoundException),
)
async def delete_item(
    shopping_id: int,
    service: ShoppingService = Depends(get_shopping_service),
):
    await service.delete_item(shopping_id)
