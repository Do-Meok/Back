"""
OpenAI의 임베딩 모델과 PGVector 기반의 Vector Store를 활용해
유사한 레시피 문서를 검색하는 RAG 서비스용 Retriever 클래스
"""

from collections.abc import Callable
from functools import lru_cache

import openai
import psycopg
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from core.config import settings
from core.exception.exceptions import DatabaseException, ExternalServiceException
from domains.rag.mapper import normalize_ingredient_name

# 보유 재료 배열이 recipe의 ingredient_names를 완전히 포함하는(100% 일치) 레시피를 찾는 쿼리.
# ingredient_names 컬럼은 scripts/backfill_ingredient_names.py 로 백필하고 GIN 인덱스를 생성해두었다.
_EXACT_MATCH_QUERY = """
    SELECT e.document, e.cmetadata
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
    WHERE c.name = %s
      AND e.ingredient_names IS NOT NULL
      AND cardinality(e.ingredient_names) > 0
      AND e.ingredient_names <@ %s::text[]
    ORDER BY cardinality(e.ingredient_names) DESC
    LIMIT %s
"""


class RecipeRetriever:
    def __init__(
        self,
        vector_store: PGVector,
        connection_factory: Callable[[], psycopg.Connection] | None = None,
        collection_name: str = "recipe_vectors",
    ):
        self._vector_store = vector_store
        self._connection_factory = connection_factory
        self._collection_name = collection_name

    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        try:
            return self._vector_store.similarity_search_with_score(query, k=k)
        except openai.OpenAIError as e:
            raise ExternalServiceException(detail="레시피 임베딩 요청 중 오류가 발생했습니다.") from e
        except psycopg.Error as e:
            raise DatabaseException(detail="레시피 벡터 검색 중 DB 오류가 발생했습니다.") from e
        except Exception as e:
            raise ExternalServiceException(detail="레시피 벡터 검색 중 외부 서비스 오류가 발생했습니다.") from e

    def search_exact_matches(self, owned_ingredient_names: list[str], limit: int) -> list[tuple[Document, float]]:
        """보유 재료만으로 100% 조리 가능한(부족 재료 0개) 레시피를 SQL containment로 검색한다."""
        if self._connection_factory is None or limit <= 0:
            return []

        normalized = sorted({normalize_ingredient_name(name) for name in owned_ingredient_names if name.strip()})
        if not normalized:
            return []

        try:
            with self._connection_factory() as conn, conn.cursor() as cur:
                cur.execute(_EXACT_MATCH_QUERY, (self._collection_name, normalized, limit))
                rows = cur.fetchall()
        except psycopg.Error as e:
            raise DatabaseException(detail="레시피 완전일치 검색 중 DB 오류가 발생했습니다.") from e

        return [(Document(page_content=document, metadata=metadata or {}), 0.0) for document, metadata in rows]


@lru_cache
def get_recipe_retriever() -> RecipeRetriever:
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )
    vector_store = PGVector(
        embeddings=embeddings,
        connection=settings.rag_url,
        collection_name="recipe_vectors",
    )
    dsn = settings.rag_url.replace("postgresql+psycopg://", "postgresql://")
    return RecipeRetriever(
        vector_store=vector_store,
        connection_factory=lambda: psycopg.connect(dsn),
        collection_name="recipe_vectors",
    )
