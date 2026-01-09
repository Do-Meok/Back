from core.exception.exceptions import BaseCustomException


class IngredientNotFoundException(BaseCustomException):
    def __init__(self, detail="해당 재료가 존재하지 않습니다"):
        super().__init__(status_code=404, detail=detail, code="INGREDIENT_NOT_FOUND")


class ValueNotFoundException(BaseCustomException):
    def __init__(self, detail="유통기한 또는 보관 장소가 적혀있지 않습니다."):
        super().__init__(status_code=404, detail=detail, code="VALUE_NOT_FOUND")
