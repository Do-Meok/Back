"""
OpenAI의 임베딩 모델과 PGVector 기반의 Vector Store를 활용해
유사한 레시피 문서를 검색하는 RAG 서비스용 Retriever 클래스
"""

from functools import lru_cache

import openai
import psycopg
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from core.config import settings
from core.exception.exceptions import DatabaseException, ExternalServiceException


class RecipeRetriever:
    def __init__(self, vector_store: PGVector):
        self._vector_store = vector_store

    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        try:
            return self._vector_store.similarity_search_with_score(query, k=k)
        except openai.OpenAIError as e:
            raise ExternalServiceException(detail="레시피 임베딩 요청 중 오류가 발생했습니다.") from e
        except psycopg.Error as e:
            raise DatabaseException(detail="레시피 벡터 검색 중 DB 오류가 발생했습니다.") from e
        except Exception as e:
            raise DatabaseException(detail="레시피 벡터 검색 중 DB 오류가 발생했습니다.") from e


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
    return RecipeRetriever(vector_store=vector_store)
