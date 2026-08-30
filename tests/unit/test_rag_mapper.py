from langchain_core.documents import Document

from domains.rag.mapper import build_ingredient_query, map_document_to_recipe, parse_page_content, split_ingredients


def test_build_ingredient_query():
    assert build_ingredient_query(["계란", "양파"]) == "parsed_ingredients: 계란, 양파"


def test_parse_page_content():
    ingredients = parse_page_content("parsed_ingredients: 계란, 밥, 대파")

    assert ingredients == "계란, 밥, 대파"


def test_split_ingredients():
    assert split_ingredients("김, 밥, 김, 참 기름, 참기름") == [
        "김",
        "밥",
        "참 기름",
    ]


def test_map_document_torecipe():
    doc = Document(
        page_content="parsed_ingredients: 계란, 밥, 대파",
        metadata={
            "recipe_name": "계란볶음밥",
            "board_name": "한식",
            "author_name": "kim",
            "recipe_difficulty": "초급",
            "time": "15분",
        },
    )

    recipe = map_document_to_recipe(doc, 0.42, owned_ingredient_names=["계란", "양파"])
    assert recipe is not None
    assert recipe.recipe_name == "계란볶음밥"
    assert recipe.owned_ingredients == ["계란"]
    assert recipe.missing_ingredients == ["밥", "대파"]
    assert recipe.board_name == "한식"
    assert recipe.author_name == "kim"
    assert recipe.recipe_difficulty == "초급"
    assert recipe.time == "15분"
    assert recipe.score == 0.42
