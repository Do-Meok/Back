from core.exception.exceptions import BaseCustomException


class RecipeDataCorruptionException(BaseCustomException):
    def __init__(self, detail: str = "저장된 레시피 데이터가 손상되었거나 형식이 올바르지 않습니다."):
        super().__init__(status_code=500, detail=detail, code="RECIPE_DATA_CORRUPTION")


class RecipeNotFoundException(BaseCustomException):
    def __init__(self, detail: str = "레시피가 존재하지 않습니다."):
        super().__init__(status_code=404, detail=detail, code="RECIPE_NOT_FOUND")
