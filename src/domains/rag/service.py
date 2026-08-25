from domains.user.model import User
from domains.ingredient.repository import IngredientRepository

from domains.rag.retriever import RecipeRetriever

# 상수 설정
TOP_K = 5
SEARCH_CANDIDATE_K = 40 # 벡터 검색 후보
CANDIDATE_POOL_K = 15   # 필터 후 상위 풀에서 랜덤 추출

class RagService:
    def __init__(
            self,
            user: User,
            ingredient_repo: IngredientRepository,
            retriever: RecipeRetriever
    ):
        self.user = user
        self.ingredient_repo = ingredient_repo
        self.retriever = retriever