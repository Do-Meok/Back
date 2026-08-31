from domains.recipe_detail.matcher import SearchCandidate, normalize_text, pick_best_candidate


def test_normalize_text_collapses_whitespace_and_casefolds():
    assert normalize_text("  Kimchi   Jjigae  ") == "kimchi jjigae"


def test_pick_best_candidate_prefers_author_match():
    candidates = [
        SearchCandidate(recipe_id="1", title="다른요리", author="홍길동"),
        SearchCandidate(recipe_id="2", title="김치찌개", author="다른사람"),
    ]

    best = pick_best_candidate(candidates, "김치찌개", "홍길동")

    assert best is not None
    assert best.recipe_id == "1"


def test_pick_best_candidate_falls_back_to_title_containment():
    candidates = [
        SearchCandidate(recipe_id="1", title="맛있는 김치찌개 레시피", author="아무개"),
    ]

    best = pick_best_candidate(candidates, "김치찌개", "홍길동")

    assert best is not None
    assert best.recipe_id == "1"


def test_pick_best_candidate_returns_none_when_no_match():
    candidates = [
        SearchCandidate(recipe_id="1", title="된장찌개", author="다른사람"),
    ]

    assert pick_best_candidate(candidates, "김치찌개", "홍길동") is None


def test_pick_best_candidate_returns_none_for_empty_candidates():
    assert pick_best_candidate([], "김치찌개", "홍길동") is None


def test_pick_best_candidate_ranks_exact_title_match_above_partial():
    candidates = [
        SearchCandidate(recipe_id="partial", title="맛있는 김치찌개 만들기", author="아무개"),
        SearchCandidate(recipe_id="exact", title="김치찌개", author="다른사람"),
    ]

    best = pick_best_candidate(candidates, "김치찌개", "누군가")

    assert best is not None
    assert best.recipe_id == "exact"
