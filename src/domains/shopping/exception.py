from core.exception.exceptions import BaseCustomException

class ItemNotFoundException(BaseCustomException):
    def __init__(
        self,
        detail: str = "아이템이 존재하지 않습니다.",
    ):
        super().__init__(status_code=404, detail=detail, code="ITEM_NOT_FOUND")