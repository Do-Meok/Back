"""
Vector DB에서 검색된 문서(Document) 데이터를 레시피 추천 객체(RecipeRecommendation)로 변환하고,
레시피 검색 쿼리를 생성하는 RAG 보조 유틸리티
"""

from langchain_core.documents import Document

from domains.rag.schemas import RecipeRecommendation


def build_ingredient_query(names: list[str]) -> str:
    """
    식재료 이름 목록을 벡터 검색용 텍스트 쿼리로 변환
    ex) ["감자", "양파"] -> "pasred_ingredient: 감자, 양파"
    """
    return "parsed_ingredients: " + ", ".join(names)


def parse_page_content(page_content: str) -> str:
    """
    PGVector에 저장(Store)된 Document의 page_content 텍스트 파싱
    """
    for line in page_content.splitlines():
        if line.startswith("parsed_ingredients:"):
            return line.removeprefix("parsed_ingredients:").strip()
    return page_content.strip()


def split_ingredients(parsed_ingredients: str) -> list[str]:
    """
    파싱된 식재료 문자열을 비교 가능한 식재료 이름 목록으로 변환
    - 쉼표(,) 구분 및 양쪽 공백 제거
    """
    names: list[str] = []
    seen: set[str] = set()

    for part in parsed_ingredients.split(","):
        name = part.strip()
        if not name:
            continue

        # normalize_name 로직 통합 (대소문자 통합 및 내부 공백 제거)
        key = name.casefold().replace(" ", "")

        if key not in seen:
            seen.add(key)
            names.append(name)  # 원본 공백만 trim된 형태 저장

    return names

def map_document_to_recipe(
    doc: Document,
    score: float,
    owned_ingredient_names: list[str] | None = None,
) -> RecipeRecommendation | None:
    parsed_ingredients = parse_page_content(doc.page_content)
    meta = doc.metadata or {}

    recipe_name = str(meta.get("recipe_name", "") or "").strip()
    if not recipe_name:
        return None

    recipe_ingredients = split_ingredients(parsed_ingredients)
    owned_set = {ingredient.strip() for ingredient in (owned_ingredient_names or []) if ingredient.strip()}
    owned = [ingredient for ingredient in recipe_ingredients if ingredient in owned_set]
    missing = [ingredient for ingredient in recipe_ingredients if ingredient not in owned_set]

    return RecipeRecommendation(
        recipe_name=recipe_name,
        owned_ingredients=owned,
        missing_ingredients=missing,
        board_name=str(meta.get("board_name", "") or ""),
        author_name=str(meta.get("author_name", "") or ""),
        recipe_difficulty=str(meta.get("recipe_difficulty", "") or ""),
        time=str(meta.get("time", "") or ""),
        score=float(score),
    )
