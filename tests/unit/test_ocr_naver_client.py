from typing import Self

import httpx
import pytest

from core.exception.exceptions import ExternalServiceException
from domains.ocr import naver_client as naver_client_module
from domains.ocr.naver_client import extract_text


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload or {}


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
        self._response = response
        self._exception = exception

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def post(self, url: str, headers=None, data=None, files=None) -> _FakeResponse:
        if self._exception:
            raise self._exception
        assert self._response is not None
        return self._response


def _patch_client(monkeypatch, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
    monkeypatch.setattr(
        naver_client_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, exception=exception),
    )


async def test_extract_text_raises_when_config_missing():
    with pytest.raises(ExternalServiceException):
        await extract_text(b"bytes", format="jpg", api_url="", secret_key="")


async def test_extract_text_raises_on_unsupported_format():
    with pytest.raises(ExternalServiceException):
        await extract_text(b"bytes", format="gif", api_url="https://ocr.example.com", secret_key="secret")


async def test_extract_text_returns_joined_lines(monkeypatch: pytest.MonkeyPatch):
    payload = {"images": [{"fields": [{"inferText": "양파"}, {"inferText": "당근"}]}]}
    _patch_client(monkeypatch, response=_FakeResponse(200, payload))

    result = await extract_text(b"bytes", format="jpg", api_url="https://ocr.example.com", secret_key="secret")

    assert result == "양파\n당근"


async def test_extract_text_skips_blank_lines(monkeypatch: pytest.MonkeyPatch):
    payload = {"images": [{"fields": [{"inferText": "  "}, {"inferText": "당근"}]}]}
    _patch_client(monkeypatch, response=_FakeResponse(200, payload))

    result = await extract_text(b"bytes", format="png", api_url="https://ocr.example.com", secret_key="secret")

    assert result == "당근"


async def test_extract_text_raises_on_non_200(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(500))

    with pytest.raises(ExternalServiceException):
        await extract_text(b"bytes", format="jpg", api_url="https://ocr.example.com", secret_key="secret")


async def test_extract_text_raises_on_http_error(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, exception=httpx.ConnectError("연결 실패"))

    with pytest.raises(ExternalServiceException):
        await extract_text(b"bytes", format="jpg", api_url="https://ocr.example.com", secret_key="secret")


async def test_extract_text_raises_on_malformed_response(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, {"images": []}))

    with pytest.raises(ExternalServiceException):
        await extract_text(b"bytes", format="jpg", api_url="https://ocr.example.com", secret_key="secret")
