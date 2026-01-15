from fastapi import APIRouter, Depends

from core.di import get_recipe_service
from domains.recipe.exception import RecipeDataCorruptionException
from domains.recipe.schemas import SaveRecipeRequest, SavedRecipeResponse
from domains.recipe.service import RecipeService
from util.docs import create_error_response

router = APIRouter()


@router.post(
    "",
    status_code=201,
    summary="레시피 저장 API",
    response_model=SavedRecipeResponse,
    responses=create_error_response(RecipeDataCorruptionException),
)
async def save_recipe(
    request: SaveRecipeRequest, service: RecipeService = Depends(get_recipe_service)
):
    """
    레시피 저장 버튼을 누르면 LLM이 응답한 Recipe를 그대로 JSON 형태로 가져와서 저장함
    """
    return await service.save_recipe(request)


@router.get(
    "",
    status_code=200,
    summary="레시피 조회 API",
    response_model=list[SavedRecipeResponse],
)
async def get_recipes(
    service: RecipeService = Depends(get_recipe_service),
):
    return await service.get_recipes()
