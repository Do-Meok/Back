from unittest.mock import MagicMock

import openai
import psycopg
import pytest
from httpx import Request
from langchain_core.documents import Document

from core.exception.exceptions import DatabaseException, ExternalServiceException
from domains.rag.retriever import RecipeRetriever


def test_search_delegates_to_vector_store():
    store = MagicMock()
    doc = Document(page_content="recipe_name: a\nparsed_ingredients: b")
    store.similarity_search_with_score.return_value = [(doc, 0.3)]

    retriever = RecipeRetriever(vector_store=store)
    result = retriever.search("parsed_ingredients: 계란", k=5)

    store.similarity_search_with_score.assert_called_once_with("parsed_ingredients: 계란", k=5)
    assert result == [(doc, 0.3)]


def test_search_openai_error_raises_external_service_exception():
    store = MagicMock()
    request = Request("POST", "https://api.openai.com/v1/embeddings")
    store.similarity_search_with_score.side_effect = openai.APIError(
        "embedding failed",
        request=request,
        body=None,
    )

    retriever = RecipeRetriever(vector_store=store)

    with pytest.raises(ExternalServiceException) as exc_info:
        retriever.search("parsed_ingredients: 계란")

    assert exc_info.value.detail == "레시피 임베딩 요청 중 오류가 발생했습니다."
    assert isinstance(exc_info.value.__cause__, openai.APIError)


def test_search_db_error_raises_database_exception():
    store = MagicMock()
    store.similarity_search_with_score.side_effect = psycopg.OperationalError("connection failed")

    retriever = RecipeRetriever(vector_store=store)

    with pytest.raises(DatabaseException) as exc_info:
        retriever.search("parsed_ingredients: 계란")

    assert exc_info.value.detail == "레시피 벡터 검색 중 DB 오류가 발생했습니다."
    assert isinstance(exc_info.value.__cause__, psycopg.Error)


def test_search_generic_error_raises_external_service_exception():
    store = MagicMock()
    store.similarity_search_with_score.side_effect = RuntimeError("unexpected")

    retriever = RecipeRetriever(vector_store=store)

    with pytest.raises(ExternalServiceException) as exc_info:
        retriever.search("parsed_ingredients: 계란")

    assert exc_info.value.detail == "레시피 벡터 검색 중 외부 서비스 오류가 발생했습니다."
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def _make_connection_with_rows(rows: list[tuple]) -> MagicMock:
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = rows
    return conn


def test_search_exact_matches_queries_by_normalized_sorted_ingredients_and_returns_zero_score():
    conn = _make_connection_with_rows([("parsed_ingredients: 양파, 감자", {"recipe_name": "감자볶음"})])

    retriever = RecipeRetriever(
        vector_store=MagicMock(), connection_factory=lambda: conn, collection_name="recipe_vectors"
    )
    result = retriever.search_exact_matches(["양파", " 감자 "], limit=5)

    assert len(result) == 1
    doc, score = result[0]
    assert doc.page_content == "parsed_ingredients: 양파, 감자"
    assert doc.metadata == {"recipe_name": "감자볶음"}
    assert score == 0.0

    cursor = conn.cursor.return_value.__enter__.return_value
    _query, params = cursor.execute.call_args[0]
    assert params == ("recipe_vectors", ["감자", "양파"], 5)


def test_search_exact_matches_without_owned_ingredients_skips_query():
    retriever = RecipeRetriever(
        vector_store=MagicMock(), connection_factory=MagicMock(), collection_name="recipe_vectors"
    )

    assert retriever.search_exact_matches([], limit=5) == []


def test_search_exact_matches_without_connection_factory_returns_empty():
    retriever = RecipeRetriever(vector_store=MagicMock())

    assert retriever.search_exact_matches(["양파"], limit=5) == []


def test_search_exact_matches_db_error_raises_database_exception():
    conn = MagicMock()
    conn.__enter__.side_effect = psycopg.OperationalError("connection failed")

    retriever = RecipeRetriever(vector_store=MagicMock(), connection_factory=lambda: conn)

    with pytest.raises(DatabaseException) as exc_info:
        retriever.search_exact_matches(["양파"], limit=5)

    assert exc_info.value.detail == "레시피 완전일치 검색 중 DB 오류가 발생했습니다."
    assert isinstance(exc_info.value.__cause__, psycopg.Error)
