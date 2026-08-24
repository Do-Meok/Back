from fastapi import APIRouter, Depends, File, Query, UploadFile

from api.v1.deps import get_assistant_service
from core.exception.openapi import create_error_response
from domains.assistant.exceptions import (
    AIConnectionException,
    AIJsonDecodeException,
    AINullResponseException,
    AIRefusalException,
    AISchemaMismatchException,
    AIServiceException,
    AITimeoutException,
    InvalidAIRequestException,
)
from domains.assistant.schemas import (
    DetailRecipeRequest,
    DetailRecipeResponse,
    QuickRecipeRequest,
    ReceiptIngredientResponse,
    RecommendationResponse,
    SearchRecipeRequest,
)
from domains.assistant.service import AssistantService

router = APIRouter()

COMMON_AI_EXCEPTIONS = [
    AIServiceException,  # 503: OpenAI API 키/서버 에러
    AIConnectionException,  # 503: 네트워크 연결 실패
    AITimeoutException,  # 504: 응답 시간 초과
    AIJsonDecodeException,  # 500: JSON 파싱 실패
    AISchemaMismatchException,  # 500: 필수 필드 누락
    AINullResponseException,  # 500: 빈 응답
]


@router.get(
    "/recommendations",
    status_code=200,
    summary="보유 식재료 기반 메뉴 추천 (4가지)",
    response_model=RecommendationResponse,
    responses=create_error_response(
        InvalidAIRequestException,
        *COMMON_AI_EXCEPTIONS,
    ),
)
async def get_recommendations(
    force_refresh: bool = Query(False, description="True로 설정 시 기존 캐시를 무시하고 AI를 새로 호출합니다."),
    service: AssistantService = Depends(get_assistant_service),
):
    return await service.recommend_menus(force_refresh=force_refresh)


@router.post(
    "/detail",
    status_code=200,
    summary="선택한 메뉴의 상세 조리법 생성",
    response_model=DetailRecipeResponse,
    responses=create_error_response(
        AIRefusalException,  # 400: AI가 요리가 아니라고 판단하여 거부할 때
        *COMMON_AI_EXCEPTIONS,  # 5xx
    ),
)
async def get_recipe_detail(
    request: DetailRecipeRequest,
    service: AssistantService = Depends(get_assistant_service),
):
    """
    추천받은 요리 중 하나를 선택했을 때, 구체적인 레시피를 제공 -> 추천받았을 때의 JSON으로 해야함.
    """
    return await service.generate_recipe_detail(request)


@router.post(
    "/search",
    status_code=200,
    summary="요리 이름으로 레시피 검색",
    response_model=DetailRecipeResponse,
    responses=create_error_response(
        InvalidAIRequestException,  # 400: 검색어(food_name)가 비어있을 때
        AIRefusalException,  # 400: 검색어가 요리가 아닐 때 (예: '벽돌')
        *COMMON_AI_EXCEPTIONS,  # 5xx
    ),
)
async def search_recipe_by_name(
    request: SearchRecipeRequest,
    service: AssistantService = Depends(get_assistant_service),
):
    """
    사용자가 입력한 요리명(예: '김치찌개')에 대한 정석 레시피를 알려줌
    """
    return await service.search_recipe(request.food)


@router.post(
    "/quick",
    status_code=200,
    summary="대화형 재료 입력 기반 즉시 추천",
    response_model=DetailRecipeResponse,
    responses=create_error_response(
        InvalidAIRequestException,  # 400: 채팅 입력(chat)이 비어있을 때
        AIRefusalException,  # 400: 입력 내용이 부적절할 때
        *COMMON_AI_EXCEPTIONS,  # 5xx
    ),
)
async def get_quick_recipe(
    request: QuickRecipeRequest,
    service: AssistantService = Depends(get_assistant_service),
):
    """
    '계란' 입력하면
    AI가 계란이 들어가는 최적의 요리 1개를 선정하여 즉시 상세 레시피를 제공함
    """
    return await service.get_quick_recipe(request.chat)


@router.post(
    "/receipt/extract", response_model=ReceiptIngredientResponse, status_code=200, summary="영수증 인식 및 식재료 추출"
)
async def extract_ingredients_from_receipt(
    file: UploadFile = File(...), service: AssistantService = Depends(get_assistant_service)
):
    """
    영수증 사진을 업로드하면 식재료 목록을 반환
    1. OCR로 텍스트 추출
    2. LLM으로 식재료 필터링
    """
    return await service.process_receipt_image(file)
