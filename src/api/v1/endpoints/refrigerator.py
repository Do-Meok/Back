from fastapi import APIRouter, Depends

from core.di import get_refrigerator_service
from domains.refrigerator.schemas import AddRefrigeratorRequest, GetRefrigeratorResponse
from domains.refrigerator.service import RefrigeratorService

router = APIRouter()


@router.post("", status_code=201)
async def add_refrigerator(
    request: AddRefrigeratorRequest,
    service: RefrigeratorService = Depends(get_refrigerator_service),
):
    return await service.add_refrigerator(request)

@router.get("/{refrigerator_id}", response_model=GetRefrigeratorResponse)
async def get_refrigerator(
    refrigerator_id: int,
    service: RefrigeratorService = Depends(get_refrigerator_service),
):
    """
    특정 냉장고의 상세 정보(칸 정보 포함)를 조회합니다.
    """
    return await service.get_refrigerator(refrigerator_id)