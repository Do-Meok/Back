from pydantic import BaseModel, Field


class RecipeRecommendation(BaseModel):
    recipe_name: str = Field(description="레시피 명칭")
    owned_ingredients: list[str] = Field(
        default_factory=list,
        description="보유중인 식재료",
    )
    missing_ingredients: list[str] = Field(
        default_factory=list,
        description="보유중이지 않은 식재료",
    )
    board_name: str = Field(default="", description="게시판 이름")
    author_name: str = Field(default="", description="작성자 이름")
    recipe_difficulty: str = Field(default="", description="난이도")
    time: str = Field(default="", description="조리 시간")
    score: float = Field(description="보유 재료 매칭률(보유 재료 수 / 전체 필요 재료 수, 0~1, 높을수록 많이 보유)")


class RecipeRecommendationResponse(BaseModel):
    ingredients_used: list[str]
    recipes: list[RecipeRecommendation]
    quota_remaining: int = Field(description="오늘 남은 레시피 추천 요청 가능 횟수")
