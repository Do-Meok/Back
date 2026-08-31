import uuid
from unittest.mock import AsyncMock

import pytest

from core.exception.exceptions import BadRequestException
from domains.ocr.service import MAX_IMAGE_BYTES, OcrService


@pytest.fixture
def extract_text_fn() -> AsyncMock:
    return AsyncMock(return_value="영수증 텍스트")


@pytest.fixture
def parse_receipt_text_fn() -> AsyncMock:
    return AsyncMock(return_value=["양파", "당근"])


@pytest.fixture
def ocr_service(extract_text_fn: AsyncMock, parse_receipt_text_fn: AsyncMock) -> OcrService:
    return OcrService(
        api_url="https://ocr.example.com",
        secret_key="secret",
        openai_api_key="key",
        llm_model="gpt",
        extract_text_fn=extract_text_fn,
        parse_receipt_text_fn=parse_receipt_text_fn,
        user_id=uuid.uuid4(),
    )


async def test_parse_receipt_returns_ingredients(
    ocr_service: OcrService, extract_text_fn: AsyncMock, parse_receipt_text_fn: AsyncMock
):
    result = await ocr_service.parse_receipt(b"image-bytes", "image/jpeg", "receipt.jpg")

    assert result.ingredients == ["양파", "당근"]
    extract_text_fn.assert_awaited_once_with(
        b"image-bytes", format="jpg", api_url="https://ocr.example.com", secret_key="secret"
    )
    parse_receipt_text_fn.assert_awaited_once_with("영수증 텍스트", api_key="key", model="gpt")


async def test_parse_receipt_resolves_format_from_filename_when_content_type_missing(
    ocr_service: OcrService, extract_text_fn: AsyncMock
):
    await ocr_service.parse_receipt(b"image-bytes", None, "receipt.png")

    extract_text_fn.assert_awaited_once_with(
        b"image-bytes", format="png", api_url="https://ocr.example.com", secret_key="secret"
    )


async def test_parse_receipt_raises_when_format_unresolvable(ocr_service: OcrService):
    with pytest.raises(BadRequestException):
        await ocr_service.parse_receipt(b"image-bytes", None, None)


async def test_parse_receipt_raises_when_image_too_large(ocr_service: OcrService):
    too_large = b"x" * (MAX_IMAGE_BYTES + 1)

    with pytest.raises(BadRequestException):
        await ocr_service.parse_receipt(too_large, "image/jpeg", "receipt.jpg")


async def test_parse_receipt_raises_when_image_empty(ocr_service: OcrService):
    with pytest.raises(BadRequestException):
        await ocr_service.parse_receipt(b"", "image/jpeg", "receipt.jpg")
