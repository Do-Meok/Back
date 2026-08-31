"""
KST(한국 시간) 날짜 단위로 리셋되는 일일 사용량 제한을 Redis로 관리
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from redis.asyncio import Redis

from core.exception.exceptions import ExternalServiceException, RateLimitExceededException
from core.timezone import KST

KIND_RAG_SEARCH = "rag_search"
KIND_EMAIL_SEND = "email_send"

RAG_SEARCH_DAILY_LIMIT = 5
EMAIL_SEND_DAILY_LIMIT = 5


@dataclass(frozen=True)
class QuotaInfo:
    limit: int
    used: int
    remaining: int


def _kst_today() -> date:
    return datetime.now(KST).date()


def _seconds_until_kst_midnight() -> int:
    now = datetime.now(KST)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((tomorrow - now).total_seconds()))


class DailyQuotaStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, kind: str, identifier: str) -> str:
        return f"quota:{kind}:{identifier.lower()}:{_kst_today().isoformat()}"

    async def consume(self, kind: str, identifier: str, limit: int) -> QuotaInfo:
        """
        사용량 1 소모 후 남은 횟수를 반환. 한도를 초과하면 RateLimitExceededException
        """
        key = self._key(kind, identifier)
        try:
            used = await self._redis.incr(key)
            if used == 1:
                await self._redis.expire(key, _seconds_until_kst_midnight())
        except Exception as exc:
            raise ExternalServiceException(detail="사용량 확인 중 오류가 발생했습니다.") from exc

        if used > limit:
            raise RateLimitExceededException(detail=f"오늘 사용 가능한 횟수를 모두 사용했습니다. (일일 {limit}회 제한)")
        return QuotaInfo(limit=limit, used=used, remaining=limit - used)

    async def get_remaining(self, kind: str, identifier: str, limit: int) -> QuotaInfo:
        """
        소모하지 않고 현재까지의 사용량만 조회
        """
        key = self._key(kind, identifier)
        try:
            raw = await self._redis.get(key)
        except Exception as exc:
            raise ExternalServiceException(detail="사용량 확인 중 오류가 발생했습니다.") from exc

        used = int(raw) if raw else 0
        return QuotaInfo(limit=limit, used=used, remaining=max(0, limit - used))
