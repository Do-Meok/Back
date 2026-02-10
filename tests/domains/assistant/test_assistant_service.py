import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from fastapi import UploadFile
from redis.asyncio import Redis

# 실제 프로젝트 경로에 맞게 import 경로를 확인해주세요.
from domains.assistant.service import AssistantService, LIMIT_RECIPE_DAILY, LIMIT_OCR_DAILY
from domains.assistant.exceptions import InvalidAIRequestException
from domains.assistant.schemas import (
    RecommendationResponse,
    RecommendationItem,
    DetailRecipeRequest,
    DetailRecipeResponse,
    IngredientDetail
)
from domains.user.models import User


@pytest.mark.asyncio
class TestAssistantService:
    @pytest.fixture
    def mock_deps(self):
        """테스트에 필요한 의존성(User, Repo, LLM, Redis)을 Mock 객체로 생성"""
        user = User(id="user-123", email="test@test.com")
        repo = AsyncMock()
        handler = AsyncMock()
        redis = AsyncMock()

        # Redis incr 기본값 (한도 통과: 1번째 요청)
        redis.incr.return_value = 1

        return user, repo, handler, redis

    # ----------------------------------------------------------------
    # 1. 메뉴 추천 (Recommend Menus) 테스트
    # ----------------------------------------------------------------
    async def test_recommend_menus_success(self, mock_deps):
        """[성공] 메뉴 추천: 한도 내 요청 + 재료 있음 + 이미지 URL 매핑 확인"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given 1: 재료 설정
        mock_ingredients = [MagicMock(ingredient_name="양파"), MagicMock(ingredient_name="계란")]
        repo.get_ingredients.return_value = mock_ingredients

        # Given 2: LLM 응답 설정
        mock_recipe = RecommendationItem(
            food="계란말이",
            food_en="Egg Roll",
            use_ingredients=["계란", "양파"],
            difficulty=1,
            image_url=None  # 초기엔 없음
        )
        llm_response = RecommendationResponse(recipes=[mock_recipe])
        handler.recommend_menus.return_value = llm_response

        # Given 3: 이미지 검색 메서드 Mocking (실제 네트워크 차단)
        with patch.object(service, '_fetch_unsplash_image', return_value="https://fake-url.com/egg.jpg") as mock_fetch:
            # When
            result = await service.recommend_menus()

            # Then
            # Redis 한도 체크 확인
            today_str = datetime.now().strftime("%Y-%m-%d")
            expected_key = f"limit:recipe:{user.id}:{today_str}"
            redis.incr.assert_called_with(expected_key)

            # LLM 호출 확인
            handler.recommend_menus.assert_called_once_with(["양파", "계란"])

            # 이미지 검색 호출 확인 ("Egg Roll"로 검색했는지)
            mock_fetch.assert_called()
            mock_fetch.assert_any_call("Egg Roll")

            # 결과 검증 (객체 반환 및 URL 주입 확인)
            assert isinstance(result, RecommendationResponse)
            assert result.recipes[0].food == "계란말이"
            assert result.recipes[0].image_url == "https://fake-url.com/egg.jpg"

    async def test_recommend_menus_limit_exceeded(self, mock_deps):
        """[실패] 일일 한도 초과 시 에러 발생"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given: 한도 초과 설정
        redis.incr.return_value = LIMIT_RECIPE_DAILY + 1

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "한도" in str(exc.value.detail)
        redis.decr.assert_called_once()
        handler.recommend_menus.assert_not_called()

    async def test_recommend_menus_no_ingredients(self, mock_deps):
        """[실패] 냉장고에 재료가 없을 때 에러 발생"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given: 재료 없음
        repo.get_ingredients.return_value = []

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "재료가 하나도 없어요" in str(exc.value.detail)

    # ----------------------------------------------------------------
    # 2. 상세 레시피 생성 (Detail Recipe) 테스트
    # ----------------------------------------------------------------
    async def test_generate_recipe_detail_success(self, mock_deps):
        """[성공] 상세 레시피 생성 시 이미지 URL이 첨부되는지 테스트"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given
        request = DetailRecipeRequest(food="라면", use_ingredients=["계란"], difficulty=1)

        # LLM 응답 Mock
        mock_response = DetailRecipeResponse(
            food="라면",
            food_en="Ramen",
            use_ingredients=[IngredientDetail(name="계란", amount="1개")],
            steps=["끓인다"],
            tip="맛있다",
            image_url=None
        )
        handler.generate_detail.return_value = mock_response

        # Image Fetch Mock
        with patch.object(service, '_fetch_unsplash_image', return_value="https://fake.com/ramen.jpg") as mock_fetch:
            # When
            result = await service.generate_recipe_detail(request)

            # Then
            assert result.food == "라면"
            assert result.image_url == "https://fake.com/ramen.jpg"  # 이미지 주입 확인

            handler.generate_detail.assert_called_once()
            mock_fetch.assert_called_once_with("Ramen")
            redis.incr.assert_called()

    # ----------------------------------------------------------------
    # 3. 레시피 검색 (Search Recipe) 테스트
    # ----------------------------------------------------------------
    async def test_search_recipe_success(self, mock_deps):
        """[성공] 레시피 검색 시 이미지 URL이 첨부되는지 테스트"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given
        food_name = "김치찌개"

        mock_response = DetailRecipeResponse(
            food="김치찌개",
            food_en="Kimchi Stew",
            use_ingredients=[],
            steps=[],
            tip="",
            image_url=None
        )
        handler.search_recipe.return_value = mock_response

        with patch.object(service, '_fetch_unsplash_image', return_value="https://fake.com/kimchi.jpg") as mock_fetch:
            # When
            result = await service.search_recipe(food_name)

            # Then
            assert result.image_url == "https://fake.com/kimchi.jpg"
            handler.search_recipe.assert_called_once_with(food_name)
            mock_fetch.assert_called_once_with("Kimchi Stew")
            redis.incr.assert_called()

    # ----------------------------------------------------------------
    # 4. 퀵 레시피 (Quick Recipe) 테스트
    # ----------------------------------------------------------------
    async def test_get_quick_recipe_success(self, mock_deps):
        """[성공] 퀵 레시피 생성 시 이미지 URL 첨부 (food_en 없을 때 Fallback 테스트)"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given
        chat = "배고파"

        # LLM 응답 Mock (food_en이 None인 경우)
        mock_response = DetailRecipeResponse(
            food="간장계란밥",
            food_en=None,
            use_ingredients=[],
            steps=[],
            tip="",
            image_url=None
        )
        handler.quick_recipe.return_value = mock_response

        with patch.object(service, '_fetch_unsplash_image', return_value="https://fake.com/rice.jpg") as mock_fetch:
            # When
            result = await service.get_quick_recipe(chat)

            # Then
            assert result.image_url == "https://fake.com/rice.jpg"

            # food_en이 없으므로 "한글명 + food" 조합으로 검색했는지 확인
            mock_fetch.assert_called_once_with("간장계란밥 food")
            redis.incr.assert_called()

    # ----------------------------------------------------------------
    # 5. 영수증 OCR 처리 (Receipt Image) 테스트
    # ----------------------------------------------------------------
    async def test_process_receipt_image_success(self, mock_deps):
        """[성공] 영수증 처리: 파일 검사 -> 한도 -> OCR -> LLM"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given 1: Mock UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b"valid_image_bytes"

        # Given 2: OCR 및 LLM Mocking
        with patch("domains.assistant.service.ocr_client") as mock_ocr:
            mock_ocr.get_ocr_text = AsyncMock(return_value="콩나물 500원")
            handler.parse_receipt_ingredients.return_value = {"ingredients": ["콩나물"]}

            # When
            result = await service.process_receipt_image(mock_file)

            # Then
            mock_file.read.assert_called_once()

            # OCR 한도 키 확인
            args, _ = redis.incr.call_args
            assert "limit:ocr" in args[0]

            mock_ocr.get_ocr_text.assert_called_once_with(b"valid_image_bytes", "jpg")
            handler.parse_receipt_ingredients.assert_called_once_with("콩나물 500원")
            assert result == {"ingredients": ["콩나물"]}

    async def test_process_receipt_image_wrong_content_type(self, mock_deps):
        """[실패] 이미지가 아닌 파일 업로드 시 에러"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"

        with pytest.raises(InvalidAIRequestException) as exc:
            await service.process_receipt_image(mock_file)

        assert "이미지 파일만" in str(exc.value.detail)
        redis.incr.assert_not_called()

    async def test_process_receipt_image_empty_content(self, mock_deps):
        """[실패] 파일 내용이 비어있을 때 에러"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "empty.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b""

        with pytest.raises(InvalidAIRequestException) as exc:
            await service.process_receipt_image(mock_file)

        assert "파일 내용이 비어있습니다" in str(exc.value.detail)
        redis.incr.assert_called_once()

    # ----------------------------------------------------------------
    # 6. Unsplash API 연동 (Private Method) 테스트
    # ----------------------------------------------------------------
    async def test_fetch_unsplash_image_integration(self, mock_deps):
        """[단위] _fetch_unsplash_image 메서드가 httpx를 올바르게 호출하는지 테스트"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # httpx.AsyncClient Mocking
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value

            # Mock Response 설정
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [{"urls": {"regular": "https://api-result.com/img.jpg"}}]
            }
            mock_client.get.return_value = mock_response

            # When
            url = await service._fetch_unsplash_image("Kimchi")

            # Then
            assert url == "https://api-result.com/img.jpg"
            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args.kwargs
            assert call_kwargs['params']['query'] == "Kimchi"