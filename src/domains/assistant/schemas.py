from pydantic import BaseModel, Field


# --- LLM 관련 ---
class RecommendationItem(BaseModel):
    food: str = Field(..., description="요리 이름")
    food_en: str = Field(..., description="요리 이름 (영어) - 이미지 추출용")
    use_ingredients: list[str] = Field(..., description="사용된 재료 이름 목록")
    difficulty: int = Field(..., description="난이도 (1-5)")
    image_url: str | None = Field(None, description="요리 이미지 URL")


class RecommendationResponse(BaseModel):
    recipes: list[RecommendationItem]


class DetailRecipeRequest(BaseModel):
    food: str = Field(..., description="요리 이름")
    use_ingredients: list[str] = Field(..., description="사용된 재료 이름 목록")
    difficulty: int = Field(..., description="난이도 (1-5)")


class IngredientDetail(BaseModel):
    name: str = Field(..., description="재료명")
    amount: str = Field(..., description="계량 정보 (예: 200g, 1개)")


class DetailRecipeResponse(BaseModel):
    food: str = Field(..., description="요리 이름 (한글)")
    food_en: str | None = Field(None, description="요리 이름 (영어) - 이미지 검색용")  # 추가
    use_ingredients: list[IngredientDetail]
    steps: list[str]
    tip: str
    image_url: str | None = Field(None, description="요리 이미지 URL")  # 추가


class SearchRecipeRequest(BaseModel):
    food: str = Field(..., description="검색할 요리 이름 (예: 김치찌개)")


class QuickRecipeRequest(BaseModel):
    chat: str = Field(..., description="가지고 있는 재료나 상황 설명 (예: 계란)")


# --- OCR 관련 ---
class ReceiptIngredientResponse(BaseModel):
    ingredients: list[str] = Field(..., description="영수증에서 추출된 식재료 이름 목록")
