"""
이메일 인증 관련 Redis
6자리 코드 생성/TTL 저장/1회성 삭제/재발송 대기시간
"""

import hashlib
import json
import secrets

from redis.asyncio import Redis
from redis.exceptions import WatchError

from core.exception.codes import ErrorCode
from core.exception.exceptions import BadRequestException, ExternalServiceException

PURPOSE_SIGNUP = "signup"
PURPOSE_PASSWORD_RESET = "password_reset"
CODE_TTL_SECONDS = 180  # 이메일 인증 제한시간
MAX_ATTEMPTS = 5  # 이메일 별 최대 인증횟수


def hash_email_code(code: str) -> str:
    """
    이메일 인증 코드를 6자리 코드로 해시해서 반환
    """
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_email_code() -> str:
    """
    0부터 999999사이의 정수를 뽑고, padding함(8-> 000008)
    """
    return f"{secrets.randbelow(1_000_000):06d}"


class VerificationCodeStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _code_key(self, purpose: str, email: str) -> str:
        """
        인증 코드가 저장되는 Redis 키 생성
        purpose: 회원가입 인증, 비밀번호 재설정 인증
        """
        return f"email_code:{purpose}:{email.lower()}"

    def _resend_used_key(self, purpose: str, email: str) -> str:
        """
        재발송 사용 여부 확인용, 존재 자체로 판단
        """
        return f"email_code_resend_used:{purpose}:{email.lower()}"

    async def _store_code(self, purpose: str, email: str) -> str:
        """
        코드를 만들어 TTL로 저장한 뒤, 평문 코드 반환
        """
        code = generate_email_code()
        payload = json.dumps({"hash": hash_email_code(code), "attempts": 0})
        await self._redis.set(
            self._code_key(purpose, email),
            payload,
            ex=CODE_TTL_SECONDS,
        )
        return code

    async def issue(self, purpose: str, email: str) -> str:
        """
        인증 사이클 시작할 때 호출하기 전에 먼저 resend_key가 있다면 제거함.
        새 코드가 생기면서 기존에 있던 재발송 카운터를 0으로 맞춰야하기 때문
        """
        email = email.lower()
        try:
            await self._redis.delete(self._resend_used_key(purpose, email))
            return await self._store_code(purpose, email)
        except Exception as exc:
            raise ExternalServiceException("인증 코드 저장에 실패했습니다.") from exc

    async def resend(self, purpose: str, email: str) -> str:
        """
        재발송 관련
        """
        email = email.lower()
        resend_key = self._resend_used_key(purpose, email)
        try:
            resend_set = await self._redis.set(
                resend_key,
                "1",
                ex=CODE_TTL_SECONDS,
                nx=True,
            )
            if not resend_set:
                raise BadRequestException(
                    code=ErrorCode.VERIFICATION_COOLDOWN,
                    detail="인증 코드 재발송은 1회만 가능합니다.",
                )
            return await self._store_code(purpose, email)
        except BadRequestException:
            raise
        except Exception as exc:
            raise ExternalServiceException("인증 코드 저장에 실패했습니다.") from exc

    async def verify(self, purpose: str, email: str, code: str) -> None:
        """
        검증 관련
        """
        email = email.lower()
        key = self._code_key(purpose, email)
        try:
            while True:
                try:
                    async with self._redis.pipeline() as pipe:
                        await pipe.watch(key)
                        raw = await pipe.get(key)
                        if raw is None:
                            raise BadRequestException(
                                code=ErrorCode.INVALID_VERIFICATION_CODE,
                                detail=("인증 코드가 올바르지 않거나 만료되었습니다."),
                            )

                        data = json.loads(raw)
                        if data["hash"] == hash_email_code(code):
                            pipe.multi()
                            pipe.delete(key)
                            pipe.delete(self._resend_used_key(purpose, email))
                            await pipe.execute()
                            return

                        attempts = int(data.get("attempts", 0)) + 1
                        if attempts >= MAX_ATTEMPTS:
                            pipe.multi()
                            pipe.delete(key)
                        else:
                            ttl = await pipe.ttl(key)
                            if ttl <= 0:
                                raise BadRequestException(
                                    code=ErrorCode.INVALID_VERIFICATION_CODE,
                                    detail=("인증 코드가 올바르지 않거나 만료되었습니다."),
                                )
                            data["attempts"] = attempts
                            pipe.multi()
                            pipe.set(key, json.dumps(data), ex=ttl)

                        await pipe.execute()
                        raise BadRequestException(
                            code=ErrorCode.INVALID_VERIFICATION_CODE,
                            detail="인증 코드가 올바르지 않거나 만료되었습니다.",
                        )
                except WatchError:
                    continue
        except BadRequestException:
            raise
        except Exception as exc:
            raise ExternalServiceException("인증 코드 검증에 실패했습니다.") from exc
