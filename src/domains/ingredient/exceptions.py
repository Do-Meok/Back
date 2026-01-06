from core.exception.exceptions import BaseCustomException


class IngredientConflictException(BaseCustomException):
    def __init__(self, detail="식재료 관련 제약 조건 오류 (중복 등)"):
        super().__init__(status_code=409, detail=detail, code="INGREDIENT_CONFLICT")


class IngredientNotFoundException(BaseCustomException):
    def __init__(self, detail="해당 재료가 존재하지 않아 삭제할 수 없습니다"):
        super().__init__(status_code=404, detail=detail, code="INGREDIENT_NOT_FOUND")
