import json
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from httpx import Request

from core.exception.exceptions import ExternalServiceException
from domains.ocr import llm_parser
from domains.ocr.llm_parser import _normalize_names, parse_receipt_text


def _make_client(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def test_normalize_names_dedupes_strips_and_truncates():
    long_name = "가" * 50
    names = ["  양파  ", "양파", "당근", long_name]

    result = _normalize_names(names)

    assert result == ["양파", "당근", long_name[:45]]


def test_normalize_names_skips_blank_entries():
    assert _normalize_names(["  ", "", "당근"]) == ["당근"]


async def test_parse_receipt_text_returns_normalized_ingredients(monkeypatch: pytest.MonkeyPatch):
    client = _make_client(json.dumps({"ingredients": ["양파", "양파", "당근"]}))
    monkeypatch.setattr(llm_parser, "AsyncOpenAI", MagicMock(return_value=client))

    result = await parse_receipt_text("영수증 텍스트", api_key="key", model="gpt")

    assert result == ["양파", "당근"]
    client.chat.completions.create.assert_awaited_once()


async def test_parse_receipt_text_raises_on_invalid_json(monkeypatch: pytest.MonkeyPatch):
    client = _make_client("not-json")
    monkeypatch.setattr(llm_parser, "AsyncOpenAI", MagicMock(return_value=client))

    with pytest.raises(ExternalServiceException):
        await parse_receipt_text("영수증 텍스트", api_key="key", model="gpt")


async def test_parse_receipt_text_raises_on_schema_mismatch(monkeypatch: pytest.MonkeyPatch):
    client = _make_client(json.dumps({"ingredients": "not-a-list"}))
    monkeypatch.setattr(llm_parser, "AsyncOpenAI", MagicMock(return_value=client))

    with pytest.raises(ExternalServiceException):
        await parse_receipt_text("영수증 텍스트", api_key="key", model="gpt")


async def test_parse_receipt_text_raises_on_openai_error(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    request = Request("POST", "https://api.openai.com/v1/chat/completions")
    client.chat.completions.create = AsyncMock(side_effect=openai.APIError("failed", request=request, body=None))
    monkeypatch.setattr(llm_parser, "AsyncOpenAI", MagicMock(return_value=client))

    with pytest.raises(ExternalServiceException):
        await parse_receipt_text("영수증 텍스트", api_key="key", model="gpt")
