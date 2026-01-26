from core.exception.exceptions import BaseCustomException


class RefrigeratorNotFoundException(BaseCustomException):
    def __init__(
        self,
        detail: str = "냉장고가 존재하지 않습니다.",
    ):
        super().__init__(status_code=404, detail=detail, code="REFRIGERATOR_NOT_FOUND")
