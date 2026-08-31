from typing import Self

import httpx
import pytest

from core.exception.exceptions import BadRequestException, ExternalServiceException
from domains.auth import kakao_client as kakao_client_module
from domains.auth.kakao_client import fetch_kakao_user_id


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
        self._response = response
        self._exception = exception

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def get(self, url: str, headers=None) -> _FakeResponse:
        if self._exception:
            raise self._exception
        assert self._response is not None
        return self._response


def _patch_client(monkeypatch, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
    monkeypatch.setattr(
        kakao_client_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, exception=exception),
    )


async def test_fetch_kakao_user_id_returns_id_as_string(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, {"id": 123456}))

    result = await fetch_kakao_user_id("access-token")

    assert result == "123456"


async def test_fetch_kakao_user_id_raises_on_401(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(401))

    with pytest.raises(BadRequestException):
        await fetch_kakao_user_id("access-token")


async def test_fetch_kakao_user_id_raises_on_non_200(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(500))

    with pytest.raises(ExternalServiceException):
        await fetch_kakao_user_id("access-token")


async def test_fetch_kakao_user_id_raises_when_id_missing(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, {}))

    with pytest.raises(BadRequestException):
        await fetch_kakao_user_id("access-token")


async def test_fetch_kakao_user_id_raises_on_http_error(monkeypatch: pytest.MonkeyPatch):
    _patch_client(monkeypatch, exception=httpx.ConnectError("연결 실패"))

    with pytest.raises(ExternalServiceException):
        await fetch_kakao_user_id("access-token")
