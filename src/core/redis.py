from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError

from core.config import settings

_redis: Redis | None = None


async def init_redis() -> None:
    global _redis
    try:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except (RedisError, ValueError) as exc:
        logger.warning("URL로 Redis 클라이언트를 생성하는 데 실패했습니다: {}", exc)
        raise
    try:
        await _redis.ping()
    except RedisError as exc:
        logger.warning(
            "Redis 핑(ping) 연결에 실패했습니다. 서버는 시작하지만 Redis 기반 작업은 실패할 수 있습니다: {}",
            exc,
        )


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis가 초기화되지 않았습니다.")
    return _redis
