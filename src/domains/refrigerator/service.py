from domains.refrigerator.exception import RefrigeratorNotFoundException
from domains.refrigerator.models import Refrigerator, Compartment
from domains.refrigerator.schemas import (
    AddRefrigeratorRequest,
    AddRefrigeratorResponse,
    GetRefrigeratorResponse,
)
from domains.user.models import User
from domains.refrigerator.repository import RefrigeratorRepository


class RefrigeratorService:
    def __init__(self, user: User, refrigerator_repo: RefrigeratorRepository):
        self.user = user
        self.refrigerator_repo = refrigerator_repo

    async def add_refrigerator(
        self, request: AddRefrigeratorRequest
    ) -> AddRefrigeratorResponse:
        new_refrigerator = Refrigerator(
            user_id=self.user.id,
            name=request.name,
            pos_x=request.pos_x,
            pos_y=request.pos_y,
        )

        total_slots = request.pos_x * request.pos_y

        for i in range(total_slots):
            new_compartment = Compartment(name=f"{i + 1}번칸", order_index=i)
            new_refrigerator.compartments.append(new_compartment)

        saved_refrigerator = await self.refrigerator_repo.add_refrigerator(
            new_refrigerator
        )

        return AddRefrigeratorResponse.model_validate(saved_refrigerator)

    async def get_refrigerator(self, refrigerator_id: int) -> GetRefrigeratorResponse:
        refrigerator = await self.refrigerator_repo.get_refrigerator(refrigerator_id)

        if not refrigerator:
            raise RefrigeratorNotFoundException(detail="냉장고를 찾을 수 없습니다.")

        if refrigerator.user_id != self.user.id:
            raise RefrigeratorNotFoundException(detail="접근 권한이 없는 냉장고입니다.")

        return refrigerator
