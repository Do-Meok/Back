from pydantic import BaseModel, Field


class RecipeIngredient(BaseModel):
    name: str
    amount: str = ""


class RecipeStep(BaseModel):
    order: int
    description: str


class RecipeDetailResponse(BaseModel):
    board_name: str = Field(..., description="게시글 제목")
    author_name: str = Field(..., description="작성자 이름")
    recipe_name: str = Field(..., description="레시피 명")
    source_url: str = Field(..., description="게시글 제목")
    main_image_url: str | None = None
    recipe_difficulty: str | None = None
    time: str | None = None
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    cached: bool = False
