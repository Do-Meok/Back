from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from domains.assistant.exceptions import InvalidAIRequestException
from domains.assistant.schemas import (
    DetailRecipeRequest,
    DetailRecipeResponse,
    IngredientDetail,
    RecommendationItem,
    RecommendationResponse,
)
from domains.assistant.service import LIMIT_RECIPE_DAILY, AssistantService
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

        # Redis 기본값 설정 (캐시 없음, 한도 통과)
        redis.get.return_value = None
        redis.incr.return_value = 1

        return user, repo, handler, redis

    # ----------------------------------------------------------------
    # 1. 메뉴 추천 (Recommend Menus) 테스트
    # ----------------------------------------------------------------
    async def test_recommend_menus_cache_hit(self, mock_deps):
        """[성공] 메뉴 추천: 캐시가 있을 때 AI를 호출하지 않고 캐시 반환"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given: Redis에 이미 캐시된 추천 레시피가 존재함
        mock_recipe = RecommendationItem(
            food="캐시요리", food_en="Cache Food", use_ingredients=[], difficulty=1, image_url="url"
        )
        cached_response = RecommendationResponse(recipes=[mock_recipe])
        redis.get.return_value = cached_response.model_dump_json()

        # When: force_refresh=False (기본값)으로 호출
        result = await service.recommend_menus()

        # Then: 캐시 값과 일치해야 하며, DB/LLM/한도체크는 1번도 호출되면 안 됨!
        assert result.recipes[0].food == "캐시요리"
        repo.get_ingredients.assert_not_called()
        redis.incr.assert_not_called()
        handler.recommend_menus.assert_not_called()

    async def test_recommend_menus_force_refresh(self, mock_deps):
        """[성공] 메뉴 추천: 강제 새로고침 시 캐시를 무시하고 AI 호출 및 결과 저장"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given: 재료 있음 & LLM 응답 설정
        repo.get_ingredients.return_value = [MagicMock(ingredient_name="양파")]
        mock_recipe = RecommendationItem(
            food="새로운요리", food_en="New Food", use_ingredients=[], difficulty=1, image_url=None
        )
        handler.recommend_menus.return_value = RecommendationResponse(recipes=[mock_recipe])

        # When: force_refresh=True 로 호출
        with patch.object(service, "_fetch_unsplash_image", return_value="img.jpg"):
            result = await service.recommend_menus(force_refresh=True)

        # Then: redis.get(캐시 확인)을 아예 호출 안 하거나, 넘기고 진행되어야 함.
        # AI 호출 및 Redis Set(저장)이 정상적으로 이루어졌는지 확인
        handler.recommend_menus.assert_called_once()
        redis.incr.assert_called_once()
        redis.set.assert_called_once()  # 결과 캐싱
        assert result.recipes[0].food == "새로운요리"

    async def test_recommend_menus_no_ingredients(self, mock_deps):
        """[실패] 냉장고에 재료가 없을 때 에러 발생 (한도 차감 안 됨)"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given: 캐시 없음 & DB에 재료 없음
        redis.get.return_value = None
        repo.get_ingredients.return_value = []

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "재료가 하나도 없어요" in str(exc.value.detail)
        # 핵심 검증: 재료가 없으면 일일 한도를 깎으면 안 됨!
        redis.incr.assert_not_called()
        handler.recommend_menus.assert_not_called()

    async def test_recommend_menus_limit_exceeded(self, mock_deps):
        """[실패] 일일 한도 초과 시 에러 발생"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        # Given: 재료는 있지만 한도를 초과한 상태
        repo.get_ingredients.return_value = [MagicMock(ingredient_name="양파")]
        redis.get.return_value = None
        redis.incr.return_value = LIMIT_RECIPE_DAILY + 1

        # When & Then
        with pytest.raises(InvalidAIRequestException) as exc:
            await service.recommend_menus()

        assert "한도" in str(exc.value.detail)
        redis.decr.assert_called_once()  # 깎인 한도 복구 확인
        handler.recommend_menus.assert_not_called()

    # ----------------------------------------------------------------
    # 2. 상세 레시피 생성 (Detail Recipe) 테스트
    # ----------------------------------------------------------------
    async def test_generate_recipe_detail_success(self, mock_deps):
        """[성공] 상세 레시피 생성 시 이미지 URL이 첨부되는지 테스트"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        request = DetailRecipeRequest(food="라면", use_ingredients=["계란"], difficulty=1)

        mock_response = DetailRecipeResponse(
            food="라면",
            food_en="Ramen",
            use_ingredients=[IngredientDetail(name="계란", amount="1개")],
            steps=["끓인다"],
            tip="맛있다",
            image_url=None,
        )
        handler.generate_detail.return_value = mock_response

        with patch.object(service, "_fetch_unsplash_image", return_value="https://fake.com/ramen.jpg") as mock_fetch:
            result = await service.generate_recipe_detail(request)

            assert result.food == "라면"
            assert result.image_url == "https://fake.com/ramen.jpg"

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

        food_name = "김치찌개"
        mock_response = DetailRecipeResponse(
            food="김치찌개", food_en="Kimchi Stew", use_ingredients=[], steps=[], tip="", image_url=None
        )
        handler.search_recipe.return_value = mock_response

        with patch.object(service, "_fetch_unsplash_image", return_value="https://fake.com/kimchi.jpg") as mock_fetch:
            result = await service.search_recipe(food_name)

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

        chat = "배고파"
        mock_response = DetailRecipeResponse(
            food="간장계란밥", food_en=None, use_ingredients=[], steps=[], tip="", image_url=None
        )
        handler.quick_recipe.return_value = mock_response

        with patch.object(service, "_fetch_unsplash_image", return_value="https://fake.com/rice.jpg") as mock_fetch:
            result = await service.get_quick_recipe(chat)

            assert result.image_url == "https://fake.com/rice.jpg"
            mock_fetch.assert_called_once_with("간장계란밥 food")
            redis.incr.assert_called()

    # ----------------------------------------------------------------
    # 5. 영수증 OCR 처리 (Receipt Image) 테스트
    # ----------------------------------------------------------------
    async def test_process_receipt_image_success(self, mock_deps):
        """[성공] 영수증 처리: 파일 검사 -> 한도 -> OCR -> LLM"""
        user, repo, handler, redis = mock_deps
        service = AssistantService(user, handler, repo, redis)

        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = b"valid_image_bytes"

        with patch("domains.assistant.service.ocr_client") as mock_ocr:
            mock_ocr.get_ocr_text = AsyncMock(return_value="콩나물 500원")
            handler.parse_receipt_ingredients.return_value = {"ingredients": ["콩나물"]}

            result = await service.process_receipt_image(mock_file)

            mock_file.read.assert_called_once()
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

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": [{"urls": {"regular": "https://api-result.com/img.jpg"}}]}
            mock_client.get.return_value = mock_response

            url = await service._fetch_unsplash_image("Kimchi")

            assert url == "https://api-result.com/img.jpg"
            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args.kwargs
            assert call_kwargs["params"]["query"] == "Kimchi"
