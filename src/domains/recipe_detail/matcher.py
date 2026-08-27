"""
검색된 후보 목록 중에서 특정 게시물(제목, 작성자)와 가장 일치하는 레시피 후보 1개를 선별해내는 점수 기반 로직
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchCandidate:
    recipe_id: str
    title: str
    author: str


def normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value.strip())
    return collapsed.casefold()


def _score(candidate: SearchCandidate, board_name: str, author_name: str) -> int | None:
    """
    단일 후보 점수 계산
    author_match: 작성자가 정확히 일치하는지    (+100점)
    title_exact: 제목이 완전 일치하는지       (+50점)
    title_contains: 한쪽 제목이 다른 쪽 제목을 포함하고 있는지    (+25점)
    """
    title_n = normalize_text(candidate.title)
    author_n = normalize_text(candidate.author)
    board_n = normalize_text(board_name)
    want_author = normalize_text(author_name)

    author_match = author_n == want_author and want_author != ""
    title_exact = title_n == board_n and board_n != ""
    title_contains = board_n != "" and (board_n in title_n or title_n in board_n)

    # 채택 조건: 작성자 일치 OR 제목 겹침
    if not (author_match or title_contains or title_exact):
        return None

    score = 0
    if author_match:
        score += 100
    if title_exact:
        score += 50
    elif title_contains:
        score += 25
    return score


def pick_best_candidate(
    candidates: list[SearchCandidate],
    board_name: str,
    author_name: str,
) -> SearchCandidate | None:
    """
    모든 후보를 순회하며 _score 계산하여 점수를 받은 후보들만 리스트에 담아서 가장 점수가 높은 첫 번째 후보 최종 반환
    """
    ranked: list[tuple[int, SearchCandidate]] = []
    for c in candidates:
        s = _score(c, board_name, author_name)
        if s is not None:
            ranked.append((s, c))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]
