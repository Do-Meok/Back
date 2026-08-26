'''
Vector DB에서 검색된 문서(Document) 데이터를 레시피 추천 객체(RecipeRecommendation)로 변환하고,
레시피 검색 쿼리를 생성하는 RAG 보조 유틸리티
'''
from langchain_core.documents import Document

from domains.rag.schemas import RecipeRecommendation

def build_ingredient_query(names: list[str]) -> str:
    '''
    식재료 이름 목록을 벡터 검색용 텍스트 쿼리로 변환
    ex) ["감자", "양파"] -> "pasred_ingredient: 감자, 양파"
    '''
    return "parsed_ingredients: " + ", ".join(names)

def parse_page_content(page_content: str) -> str:
    '''
    PGVector에 저장(Store)된 Document의 page_content 텍스트 파싱
    '''
    for line in page_content.splitlines():
        if line.startswith("parsed_ingredients:"):
            return line.removeprefix("parsed_ingredients:").strip()
        return page_content.strip()

def map_document_to_recipe(doc: Document, score: float) -> RecipeRecommendation | None:
    parsed_ingredients = parse_page_content(doc.page_content)
    meta = doc.metadata or {}

    recipe_name = str(meta.get("recipe_name", "") or "").strip()
    if not recipe_name:
        return None


    return RecipeRecommendation(
        recipe_name=recipe_name,
        parsed_ingredients=parsed_ingredients,
        board_name=str(meta.get("board_name", "") or ""),
        author_name=str(meta.get("author_name", "") or ""),
        recipe_difficulty=str(meta.get("recipe_difficulty", "") or ""),
        time=str(meta.get("time", "") or ""),
        score=float(score),
    )