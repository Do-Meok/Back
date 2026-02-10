import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime  # datetime 임포트 필수
from fastapi import UploadFile
from redis.asyncio import Redis

from domains.assistant.service import AssistantService, LIMIT_RECIPE_DAILY, LIMIT_OCR_DAILY
from domains.assistant.exceptions import InvalidAIRequestException
from domains.user.models import User


@pytest.mark.asyncio
class TestAssistantService:
    @pytest.fixture
    def mock_deps(self):
        """테스트에 필요한 가짜 객체들을 생성"""
        user = User(id="user-123", email="test@test.com")
        repo = AsyncMock()
        handler = AsyncMock()
        redis = AsyncMock()

        # Redis incr 기본값 (한도 통과)
        redis.incr.return_value = 1

        return user, repo, handler, redis

    async def test_recommend_menus_success(self, mock_deps):
        """[성공] 한도 내 요청이며 재료가 있을 때 정상 동작"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given
        mock_ingredients = [MagicMock(ingredient_name="양파"), MagicMock(ingredient_name="계란")]
        repo.get_ingredients.return_value = mock_ingredients

        # When
        await service.recommend_menus()

        # Then
        # [수정] ANY 대신 실제 날짜 포맷을 맞춰서 검증
        today_str = datetime.now().strftime("%Y-%m-%d")
        expected_key = f"limit:recipe:{user.id}:{today_str}"

        redis.incr.assert_called_with(expected_key)
        handler.recommend_menus.assert_called_once_with(["양파", "계란"])

    async def test_recommend_menus_limit_exceeded(self, mock_deps):
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        redis.incr.return_value = LIMIT_RECIPE_DAILY + 1

        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "한도" in str(exc.value.detail)
        redis.decr.assert_called_once()
        handler.recommend_menus.assert_not_called()

    async def test_search_recipe_success(self, mock_deps):
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        await service.search_recipe("김치찌개")

        redis.incr.assert_called()
        handler.search_recipe.assert_called_once_with("김치찌개")

    async def test_process_receipt_image_success(self, mock_deps):
        """[성공] 파일 검사 -> 한도 체크 -> OCR -> LLM 순서대로 실행"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # 1. Mock UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b"valid_image_bytes"

        # 2. Mock OCR & LLM
        with patch("domains.assistant.service.ocr_client") as mock_ocr:
            # [수정] await 가능하도록 AsyncMock으로 설정
            mock_ocr.get_ocr_text = AsyncMock(return_value="콩나물 500원")

            handler.parse_receipt_ingredients.return_value = {"ingredients": ["콩나물"]}

            # When
            await service.process_receipt_image(mock_file)

            # Then
            # OCR 호출 확인
            mock_ocr.get_ocr_text.assert_called_once()

            # Redis 호출 확인 (limit:ocr 키 포함 여부)
            args, _ = redis.incr.call_args
            assert "limit:ocr" in args[0]

            # LLM 호출 확인
            handler.parse_receipt_ingredients.assert_called_once()

    async def test_process_receipt_image_no_filename(self, mock_deps):
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = None

        with pytest.raises(InvalidAIRequestException):
            await service.process_receipt_image(mock_file)

        redis.incr.assert_not_called()

    async def test_process_receipt_image_empty_content(self, mock_deps):
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "empty.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b""

        with pytest.raises(InvalidAIRequestException):
            await service.process_receipt_image(mock_file)

        # 내용 체크 전에 한도 체크가 먼저 일어나므로 호출되어야 함
        redis.incr.assert_called_once()

    async def test_process_receipt_limit_exceeded(self, mock_deps):
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"

        redis.incr.return_value = LIMIT_OCR_DAILY + 1

        with patch("domains.assistant.service.ocr_client") as mock_ocr:
            with pytest.raises(InvalidAIRequestException):
                await service.process_receipt_image(mock_file)

            mock_ocr.get_ocr_text.assert_not_called()