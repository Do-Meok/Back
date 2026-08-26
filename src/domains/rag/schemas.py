from pydantic import BaseModel, Field


class RecipeRecommendation(BaseModel):
    recipe_name: str = Field(description="레시피 명칭")
    parsed_ingredients: str = Field(description="필요한 식재료")
    board_name: str = Field(default="", description="게시판 이름")
    author_name: str = Field(default="", description="작성자 이름")
    recipe_difficulty: str = Field(default="", description="난이도")
    time: str = Field(default="", description="조리 시간")
    score: float = Field(
        description="PGVector 거리 점수(작을수록 비슷하다는 뜻)"
    )


class RecipeRecommendationResponse(BaseModel):
    ingredients_used: list[str]
    recipes: list[RecipeRecommendation]
