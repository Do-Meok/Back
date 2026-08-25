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

def parse_page_content(page_content: str) -> tuple[str, str]:
    '''
    PGVector에 저장(Store)된 Document의 page_content 텍스트 파싱
    '''
    recipe_name = ""
    parsed_ingredients = ""
    for line in page_content.splitlines():
        if line.startswith("recipe_name:"):
            recipe_name = line.removeprefix("recipe_name:").strip()
        elif line.startswith("parsed_ingredients:"):
            parsed_ingredients = line.removeprefix("parsed_ingredients:").strip()
    return recipe_name, parsed_ingredients