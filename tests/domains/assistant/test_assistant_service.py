import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile

from domains.assistant.service import AssistantService
from domains.assistant.exceptions import InvalidAIRequestException
from domains.user.models import User


@pytest.mark.asyncio
class TestAssistantService:
    @pytest.fixture
    def mock_deps(self):
        """테스트에 필요한 가짜 객체들을 한 번에 생성"""
        user = User(id="user-123", email="test@test.com")
        repo = AsyncMock()
        handler = AsyncMock()
        return user, repo, handler

    async def test_recommend_menus_with_ingredients(self, mock_deps):
        """[성공] 재료가 있을 때, 이름을 문자열 리스트로 변환해서 Handler에 전달한다."""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # Given: DB에 재료가 2개 있음
        # (실제 Ingredient 모델 구조에 맞춰 수정 필요)
        mock_ingredients = [
            MagicMock(ingredient_name="양파"),
            MagicMock(ingredient_name="계란"),
        ]
        repo.get_ingredients.return_value = mock_ingredients

        # When
        await service.recommend_menus()

        # Then
        # 1. Repo가 올바른 User ID로 호출되었는지
        repo.get_ingredients.assert_called_once_with(user_id=user.id)
        # 2. Handler에게 ["양파", "계란"] 문자열 리스트가 넘어갔는지 (핵심!)
        handler.recommend_menus.assert_called_once_with(["양파", "계란"])

    async def test_recommend_menus_no_ingredients(self, mock_deps):
        """[실패] 재료가 없으면 Handler를 호출하지 않고 InvalidAIRequestException 발생"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # Given: DB 조회 결과가 빈 리스트
        repo.get_ingredients.return_value = []

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "재료를 먼저 등록해주세요" in str(exc.value.detail)
        # Handler는 호출되지 않아야 함 (비용 절약)
        handler.recommend_menus.assert_not_called()

    async def test_search_recipe_empty_input(self, mock_deps):
        """[실패] 검색어가 비어있으면 예외 발생"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # When & Then
        with pytest.raises(InvalidAIRequestException):
            await service.search_recipe("   ")  # 공백 입력

    async def test_quick_recipe_delegation(self, mock_deps):
        """[성공] 퀵 레시피 요청 시 Handler로 문자열이 잘 전달되는지"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # When
        await service.get_quick_recipe("계란으로 아무거나")

        # Then
        handler.quick_recipe.assert_called_once_with("계란으로 아무거나")

    async def test_process_receipt_image_success(self, mock_deps):
        """[성공] 이미지 파일 -> OCR 호출 -> LLM 호출 -> 결과 반환 흐름 확인"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # 1. Mock UploadFile (이미지 파일인 척 설정)
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b"fake_image_bytes"

        # 2. Mock OCR Client (service 파일 내부의 ocr_client를 가로챔)
        # 주의: 'domains.assistant.service' 경로는 실제 service.py 파일 위치에 맞춰야 합니다.
        with patch("domains.assistant.service.ocr_client") as mock_ocr:
            # OCR이 "삼겹살 1000원"이라는 텍스트를 리턴한다고 가정
            mock_ocr.get_ocr_text = AsyncMock(return_value="삼겹살 1000원")

            # LLM이 파싱된 결과를 리턴한다고 가정
            expected_result = {"ingredients": ["삼겹살"]}
            handler.parse_receipt_ingredients.return_value = expected_result

            # When
            result = await service.process_receipt_image(mock_file)

            # Then
            # 1. 파일 읽기 호출 확인
            mock_file.read.assert_called_once()
            # 2. OCR 호출 확인 (내용, 확장자)
            mock_ocr.get_ocr_text.assert_called_once_with(b"fake_image_bytes", "jpg")
            # 3. LLM 호출 확인 (OCR 결과 텍스트가 넘어갔는지)
            handler.parse_receipt_ingredients.assert_called_once_with("삼겹살 1000원")
            # 4. 최종 결과 확인
            assert result == expected_result

    async def test_process_receipt_image_invalid_type(self, mock_deps):
        """[실패] 이미지가 아닌 파일(txt 등)을 올리면 예외 발생"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # 1. Mock UploadFile (텍스트 파일인 척 설정)
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "memo.txt"
        mock_file.content_type = "text/plain"  # image/ 가 아님

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.process_receipt_image(mock_file)

        assert "이미지 파일만" in str(exc.value.detail)
        # OCR이나 LLM은 호출되지 않아야 함
        handler.parse_receipt_ingredients.assert_not_called()

    async def test_process_receipt_image_ocr_empty(self, mock_deps):
        """[실패] OCR 결과가 공백이면(인식 실패) 예외 발생"""
        user, repo, handler = mock_deps
        service = AssistantService(user, handler, repo)

        # 1. Mock UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "blur_image.png"
        mock_file.content_type = "image/png"
        mock_file.read.return_value = b"blur_bytes"

        # 2. Mock OCR Client
        with patch("domains.assistant.service.ocr_client") as mock_ocr:
            # OCR이 빈 문자열이나 공백만 리턴한다고 가정
            mock_ocr.get_ocr_text = AsyncMock(return_value="   ")

            # When & Then
            with pytest.raises(InvalidAIRequestException) as exc:
                await service.process_receipt_image(mock_file)

            assert "글자를 인식하지 못했습니다" in str(exc.value.detail)
            # LLM은 호출되면 안 됨 (돈 아까우니까)
            handler.parse_receipt_ingredients.assert_not_called()
