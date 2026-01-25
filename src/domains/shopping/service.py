from domains.shopping.models import Shopping
from domains.shopping.repository import ShoppingRepository
from domains.shopping.schemas import AddItemRequest, AddItemResponse, GetItemResponse
from domains.user.models import User
from domains.shopping.exception import ItemNotFoundException


class ShoppingService:
    def __init__(self, user: User, shopping_repo: ShoppingRepository):
        self.user = user
        self.shopping_repo = shopping_repo

    async def add_item(self, request: AddItemRequest) -> AddItemResponse:
        new_shopping_item = Shopping(
            user_id=self.user.id,
            item=request.item_name,
            status=False
        )
        saved_item = await self.shopping_repo.add_item(new_shopping_item)

        return AddItemResponse(
            id=saved_item.id,
            item_name=saved_item.item
        )

    async def get_list(self) -> list[GetItemResponse]:
        items = await self.shopping_repo.get_items(self.user.id)

        return [
            GetItemResponse(id=item.id, item_name=item.item)
            for item in items
        ]

    async def delete_item(self, shopping_id: int):
        is_deleted = await self.shopping_repo.delete_item(
            shopping_id=shopping_id,
            user_id=self.user.id
        )

        if not is_deleted:
            raise ItemNotFoundException(detail="삭제할 항목을 찾을 수 없습니다.")