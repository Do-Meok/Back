import asyncio
import json
import re

from bs4 import BeautifulSoup
import httpx

from core.exception.exceptions import ExternalServiceException
from domains.recipe_detail.matcher import SearchCandidate

from domains.recipe_detail.schemas import (
    RecipeDetailResponse,
    RecipeIngredient,
    RecipeStep,
)

BASE_URL = "https://www.10000recipe.com"
USER_AGENT = (
    "domeok-bot/1.0 (+https://github.com/local; personal non-commercial use)"
)

class RecipeCrawler:
    _semaphore = asyncio.Semaphore(3)   # 최대 동시 요청 수 -> 서버에 과도한 부하 주지 않도록 제어

    # 비동기 HTTP GET 요청을 보내서 사이트 요청
    async def _get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> str:
        try:
            async with self._semaphore:
                async with httpx.AsyncClient(
                    timeout=10.0,
                    headers={"User-Agent": USER_AGENT},
                ) as client:
                    response = await client.get(url, params=params)
            if response.status_code != httpx.codes.OK:
                raise ExternalServiceException("레시피 사이트 요청에 실패했어요")
            return response.text
        except ExternalServiceException:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalServiceException("레시피 사이트 요청 중 오류가 발생했어요") from exc

    # 레시피 검색 사이트에서 검색 후 검색 후보 목록 반환
    async def search(self, query: str) -> list[SearchCandidate]:
        html = await self._get(
            f"{BASE_URL}/recipe/list.html",
            params={
                "q": query.strip(),
                "order": "accuracy",    # 정확순 선택
                "lastcate": "order",
            },
        )
        try:
            return parse_search_html(html)
        except ExternalServiceException:
            raise
        except Exception as exc:
            raise ExternalServiceException("레시피 검색 결과 파싱 실패") from exc

    # 일치하는 게시글 들어가서 정보 추출하여 레시피 정보 반환
    async def fetch_detail(self, recipe_id: str) -> RecipeDetailResponse:
        html = await self._get(f"{BASE_URL}/recipe/{recipe_id}")
        try:
            detail = parse_detail_html(html, recipe_id)
            if not detail.recipe_name and not detail.ingredients and not detail.steps:
                raise ExternalServiceException("레시피 상세 정보 반환 실패")
            return detail
        except ExternalServiceException:
            raise
        except Exception as exc:
            raise ExternalServiceException("레시피 상세 정보 파싱 실패") from exc



def parse_search_html(html: str) -> list[SearchCandidate]:
    '''
    검색 결과 HTML에세 레시피 목록 항목을 순회하여 레시피 ID, 제목, 작성자 정보를 추출함
    '''
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchCandidate] = []

    for item in soup.select("li.common_sp_list_li"):
        link = item.select_one("a.common_sp_link[href]")
        if link is None:
            continue

        href = link.get("href")
        if not isinstance(href, str):
            continue

        recipe_id = href.rstrip("/").split("/")[-1]
        title = item.select_one(".common_sp_caption_tit")
        # 실제 마크업은 <a>닉네임</a> 이고, 구형/픽스처는 <b>닉네임</b> 일 수 있음
        author_el = item.select_one(".common_sp_caption_rv_name a") or item.select_one(
            ".common_sp_caption_rv_name"
        )
        results.append(
            SearchCandidate(
                recipe_id=recipe_id,
                title=title.get_text(strip=True) if title else "",
                author=author_el.get_text(strip=True) if author_el else "",
            )
        )

    return results

def _split_ingredient(raw: str) -> RecipeIngredient:
    # 식재료 분할 -> "감자 2개"와 같은 텍스트 재료 문자열을 이름 "감자"와 수량"2개"로 분리
   parts = raw.strip().split()
   if len(parts) >= 2:
       return RecipeIngredient(name=parts[0], amount=" ".join(parts[1:]))
   return RecipeIngredient(name=raw.strip(), amount="")


def _load_recipe_ld(soup: BeautifulSoup) -> dict[str, object] | None:
    """ 검색엔진용 표준 레시피 데이터(@type: "Recipe")를 찾아 JSON으로 로드 """
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue

        candidates: list[object]
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict) and isinstance(data.get("@graph"), list):
            candidates = data["@graph"]
        else:
            candidates = [data]

        for item in candidates:
            recipe_type = item.get("@type") if isinstance(item, dict) else None
            if recipe_type == "Recipe" or (
                isinstance(recipe_type, list) and "Recipe" in recipe_type
            ):
                return item

    return None


def _parse_difficulty_and_time(
    soup: BeautifulSoup, recipe: dict[str, object]
) -> tuple[str | None, str | None]:
    """
    JSON-LD 정보에서 난이도와 시간 정보를 가져오고 없으면 HTML 태그에서 수집
    """
    difficulty: str | None = None
    time_value: str | None = None

    raw_difficulty = recipe.get("recipeDifficulty") or recipe.get("difficulty")
    if isinstance(raw_difficulty, str) and raw_difficulty.strip():
        difficulty = raw_difficulty.strip()

    if difficulty is None:
        level_el = soup.select_one(
            ".view_info .view_info_level, .view_summary_info .view_info_level"
        )
        if level_el is not None:
            text = level_el.get_text(strip=True)
            if text:
                difficulty = text

    if time_value is None:
        time_el = soup.select_one(
            ".view_info .view_info_time, .view_summary_info .view_info_time"
        )
        if time_el is not None:
            text = time_el.get_text(strip=True)
            if text:
                time_value = text

    return difficulty, time_value

def parse_detail_html(html: str, recipe_id: str) -> RecipeDetailResponse:
    '''
    레시피 상세 정보 HTML을 파싱하여 정밀하게 추출함.
    '''
    soup = BeautifulSoup(html, "html.parser")
    recipe = _load_recipe_ld(soup) or {}

    image = recipe.get("image")
    if isinstance(image, list) and image:
        first_image = image[0]
        main_image = (
            first_image
            if isinstance(first_image, str)
            else first_image.get("url")
            if isinstance(first_image, dict)
            else None
        )
    elif isinstance(image, str):
        main_image = image
    else:
        main_image = None

    raw_ingredients = recipe.get("recipeIngredient")
    ingredients = [
        _split_ingredient(raw)
        for raw in raw_ingredients
        if isinstance(raw, str)
    ] if isinstance(raw_ingredients, list) else []

    raw_steps = recipe.get("recipeInstructions")
    steps: list[RecipeStep] = []
    if isinstance(raw_steps, list):
        for order, step in enumerate(raw_steps, start=1):
            if isinstance(step, dict):
                steps.append(
                    RecipeStep(
                        order=order,
                        description=step.get("text")
                        if isinstance(step.get("text"), str)
                        else "",
                    )
                )
            elif isinstance(step, str):
                steps.append(RecipeStep(order=order, description=step))

    tips: list[str] = []
    seen: set[str] = set()
    for selector in (".view_step .tip", ".view_step_tip dd"):
        for tip in soup.select(selector):
            text = tip.get_text(strip=True)
            if not text or text in seen:
                continue
            seen.add(text)
            tips.append(text)

    recipe_difficulty, time_value = _parse_difficulty_and_time(soup, recipe)

    return RecipeDetailResponse(
        board_name="",
        author_name="",
        recipe_name=recipe.get("name") if isinstance(recipe.get("name"), str) else "",
        source_url=f"{BASE_URL}/recipe/{recipe_id}",
        main_image_url=main_image,
        recipe_difficulty=recipe_difficulty,
        time=time_value,
        ingredients=ingredients,
        steps=steps,
        tips=tips,
        cached=False,
    )
