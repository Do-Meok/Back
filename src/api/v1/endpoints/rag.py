from fastapi import APIRouter, Depends, status

from api.deps import get_rag_service, get_recipe_detail_service
from core.exception.exceptions import (
    DatabaseException,
    ExternalServiceException,
    NotFoundException,
    RateLimitExceededException,
    UnAuthorizedException,
)
from core.exception.openapi import create_error_response
from domains.rag.schemas import RecipeRecommendationResponse
from domains.rag.service import RagService
from domains.recipe_detail.schemas import RecipeDetailResponse
from domains.recipe_detail.service import RecipeDetailService

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get(
    "/recommendations",
    status_code=status.HTTP_200_OK,
    response_model=RecipeRecommendationResponse,
    summary="레시피 추천",
    description="보유 재료 기반 레시피 추천(RAG 검색)",
    responses=create_error_response(
        UnAuthorizedException,
        ExternalServiceException,
        DatabaseException,
        RateLimitExceededException,
    ),
)
async def recommend_recipes(
    service: RagService = Depends(get_rag_service),
) -> RecipeRecommendationResponse:
    return await service.recommend_recipes()


@router.get(
    "/detail",
    status_code=status.HTTP_200_OK,
    summary="레시피 상세 조회",
    description="만개의 레시피 게시글명·작성자명으로 레시피 상세 정보를 크롤링 후 반환",
    response_model=RecipeDetailResponse,
    responses=create_error_response(
        UnAuthorizedException,
        NotFoundException,
        ExternalServiceException,
    ),
)
async def recipe_detail(
    board_name: str,
    author_name: str,
    service: RecipeDetailService = Depends(get_recipe_detail_service),
) -> RecipeDetailResponse:
    return await service.get_detail(board_name, author_name)
