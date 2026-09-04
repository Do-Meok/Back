import asyncio

from core.quota import KIND_RAG_SEARCH, RAG_SEARCH_DAILY_LIMIT, DailyQuotaStore
from domains.ingredient.repository import IngredientRepository
from domains.rag.mapper import build_ingredient_query, map_document_to_recipe
from domains.rag.retriever import RecipeRetriever
from domains.rag.schemas import RecipeRecommendationResponse
from domains.user.model import User

# 상수 설정
TOP_K = 5


class RagService:
    def __init__(
        self,
        user: User,
        ingredient_repo: IngredientRepository,
        retriever: RecipeRetriever,
        daily_quota_store: DailyQuotaStore,
    ):
        self.user = user
        self.ingredient_repo = ingredient_repo
        self.retriever = retriever
        self.daily_quota_store = daily_quota_store

    async def recommend_recipes(self) -> RecipeRecommendationResponse:
        ingredients = await self.ingredient_repo.get_ingredients(self.user.id)
        names = [item.ingredient_name for item in ingredients]
        if not names:
            # 실제 검색을 하지 않았으므로 소모하지 않고 남은 횟수만 조회
            quota = await self.daily_quota_store.get_remaining(
                KIND_RAG_SEARCH, str(self.user.id), RAG_SEARCH_DAILY_LIMIT
            )
            return RecipeRecommendationResponse(ingredients_used=[], recipes=[], quota_remaining=quota.remaining)

        quota = await self.daily_quota_store.consume(KIND_RAG_SEARCH, str(self.user.id), RAG_SEARCH_DAILY_LIMIT)

        query = build_ingredient_query(names)
        docs_with_scores = await asyncio.to_thread(self.retriever.search, query, k=TOP_K)

        recipes = []
        for doc, _distance in docs_with_scores:
            # 벡터 거리(_distance)는 후보 검색 순서에만 쓰이고, 노출되는 score는 재료 보유율로 별도 계산됨
            mapped = map_document_to_recipe(doc, owned_ingredient_names=names)
            if mapped is not None:
                recipes.append(mapped)

        return RecipeRecommendationResponse(
            ingredients_used=names,
            recipes=recipes,
            quota_remaining=quota.remaining,
        )
