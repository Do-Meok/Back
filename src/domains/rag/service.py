import asyncio

from core.quota import KIND_RAG_SEARCH, RAG_SEARCH_DAILY_LIMIT, DailyQuotaStore
from domains.ingredient.repository import IngredientRepository
from domains.rag.mapper import build_ingredient_query, map_document_to_recipe
from domains.rag.retriever import RecipeRetriever
from domains.rag.schemas import RecipeRecommendationResponse
from domains.user.model import User

# 상수 설정
TOP_K = 10
# 벡터 검색 1차 후보군 크기(재료 보유율로 재정렬하기 위해 최종 개수보다 넉넉히 조회)
CANDIDATE_K = 30


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

        # 1) 보유 재료만으로 부족한 것 없이 조리 가능한(100% 일치) 레시피를 SQL containment로 먼저 확보한다.
        #    임베딩 유사도와 무관하게 항상 찾아지므로, 재료를 많이 추가해도 100% 일치 레시피가 밀려나지 않는다.
        exact_docs = await asyncio.to_thread(self.retriever.search_exact_matches, names, TOP_K)

        recipes = []
        seen_keys: set[tuple[str, str, str]] = set()
        for doc, score in exact_docs:
            mapped = map_document_to_recipe(doc, score, owned_ingredient_names=names)
            if mapped is None:
                continue
            key = (mapped.recipe_name, mapped.board_name, mapped.author_name)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            recipes.append(mapped)

        # 2) 자리가 남으면 벡터 유사도 검색으로 후보를 넓게 가져와 부족 재료가 적은 순으로 채운다.
        remaining = TOP_K - len(recipes)
        if remaining > 0:
            query = build_ingredient_query(names)
            docs_with_scores = await asyncio.to_thread(self.retriever.search, query, k=CANDIDATE_K)

            fallback_candidates = []
            for doc, score in docs_with_scores:
                mapped = map_document_to_recipe(doc, score, owned_ingredient_names=names)
                if mapped is None:
                    continue
                key = (mapped.recipe_name, mapped.board_name, mapped.author_name)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                fallback_candidates.append(mapped)

            fallback_candidates.sort(key=lambda recipe: (len(recipe.missing_ingredients), recipe.score))
            recipes.extend(fallback_candidates[:remaining])

        return RecipeRecommendationResponse(
            ingredients_used=names,
            recipes=recipes,
            quota_remaining=quota.remaining,
        )
