'''
게시판 이름과 작성자 이름을 기반으로 찾은 레시피 상세 정보를 Redis에 캐싱하고 조회하는 비동기 캐시 관리 모듈
'''

import hashlib

from loguru import logger
from redis.asyncio import Redis

from domains.recipe_detail.matcher import normalize_text
from domains.recipe_detail.schemas import RecipeDetailResponse


def cache_key(board_name: str, author_name: str) -> str:
    '''
    cache_key 생성 -> 특수문자나 공백 등의 영향을 줄이고 고유한 고정 길이 키를 안전하게 만듬
    '''
    raw = f"{normalize_text(board_name)}|{normalize_text(author_name)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RecipeDetailCache:
    def __init__(self, redis: Redis, ttl_seconds: int = 86400) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _redis_key(self, key: str) -> str:
        '''
        해시 키 앞에 'recipe_detail:' 이라는 접두사를 붙여 다른 캐시 데이터와의 충돌 방지
        '''
        return f"recipe_detail:{key}"

    async def get(self, key: str) -> RecipeDetailResponse | None:
        '''
        Redis에서 캐시 데이터를 가져옴
        '''
        try:
            raw = await self._redis.get(self._redis_key(key))
        except Exception:
            logger.warning("레시피 상세 정보를 캐시에서 가져오는데 실패")
            return None
        if raw is None:
            return None
        try:
            value = RecipeDetailResponse.model_validate_json(raw)
        except Exception:
            logger.warning("레시피 상세 정보를 디코딩하는데 실패")
            return None
        return value.model_copy(update={"cached": True})

    async def set(self, key: str, value: RecipeDetailResponse) -> None:
        '''
        캐시 저장
        '''
        stored = value.model_copy(update={"cached": False})
        try:
            await self._redis.set(
                self._redis_key(key),
                stored.model_dump_json(),
                ex=self._ttl,
            )
        except Exception:
            logger.warning("recipe detail cache set failed")
