from pathlib import Path
from typing import Self
from unittest.mock import AsyncMock

import httpx
import pytest

from core.exception.exceptions import ExternalServiceException
from domains.recipe_detail import crawler as crawler_module
from domains.recipe_detail.crawler import RecipeCrawler, parse_detail_html, parse_search_html

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_parse_search_html_extracts_candidates():
    html = (FIXTURES_DIR / "10000recipe_search.html").read_text(encoding="utf-8")

    candidates = parse_search_html(html)

    assert len(candidates) == 2
    assert candidates[0].recipe_id == "6891574"
    assert candidates[0].author == "GP하루한끼"
    assert candidates[1].recipe_id == "111"
    assert candidates[1].author == "다른사람"


def test_parse_detail_html_extracts_recipe_info():
    html = (FIXTURES_DIR / "10000recipe_detail.html").read_text(encoding="utf-8")

    detail = parse_detail_html(html, "1")

    assert detail.recipe_name == "닭꼬치"
    assert detail.source_url == "https://www.10000recipe.com/recipe/1"
    assert detail.main_image_url == "https://example.com/main.jpg"
    assert detail.ingredients[0].name == "닭가슴살"
    assert detail.ingredients[0].amount == "200g"
    assert detail.steps[0].description == "재료를 준비한다."
    assert detail.steps[1].description == "굽는다."
    assert detail.tips == ["기름을 충분히 두르세요"]


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
        self._response = response
        self._exception = exception

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def get(self, url: str, params: dict | None = None) -> _FakeResponse:
        if self._exception:
            raise self._exception
        assert self._response is not None
        return self._response


def _patch_client(monkeypatch, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
    monkeypatch.setattr(
        crawler_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, exception=exception),
    )


async def test_get_raises_on_non_200(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(500))
    crawler = RecipeCrawler()

    with pytest.raises(ExternalServiceException):
        await crawler._get("https://www.10000recipe.com/recipe/list.html")


async def test_get_raises_on_http_error(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, exception=httpx.ConnectError("연결 실패"))
    crawler = RecipeCrawler()

    with pytest.raises(ExternalServiceException):
        await crawler._get("https://www.10000recipe.com/recipe/list.html")


async def test_search_returns_parsed_candidates(monkeypatch: pytest.MonkeyPatch):
    html = (FIXTURES_DIR / "10000recipe_search.html").read_text(encoding="utf-8")
    crawler = RecipeCrawler()
    monkeypatch.setattr(crawler, "_get", AsyncMock(return_value=html))

    candidates = await crawler.search("김치찌개")

    assert len(candidates) == 2
    assert candidates[0].recipe_id == "6891574"


async def test_fetch_detail_returns_parsed_detail(monkeypatch: pytest.MonkeyPatch):
    html = (FIXTURES_DIR / "10000recipe_detail.html").read_text(encoding="utf-8")
    crawler = RecipeCrawler()
    monkeypatch.setattr(crawler, "_get", AsyncMock(return_value=html))

    detail = await crawler.fetch_detail("1")

    assert detail.recipe_name == "닭꼬치"


async def test_fetch_detail_raises_when_nothing_found(monkeypatch: pytest.MonkeyPatch):
    crawler = RecipeCrawler()
    monkeypatch.setattr(crawler, "_get", AsyncMock(return_value="<html><body>없음</body></html>"))

    with pytest.raises(ExternalServiceException):
        await crawler.fetch_detail("missing")
