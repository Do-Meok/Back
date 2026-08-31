import json

import fakeredis.aioredis
import pytest

from core.exception.exceptions import BadRequestException
from domains.auth.verification_store import (
    MAX_ATTEMPTS,
    PURPOSE_SIGNUP,
    VerificationCodeStore,
    generate_email_code,
    hash_email_code,
)


@pytest.fixture
async def redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


@pytest.fixture
def store(redis) -> VerificationCodeStore:
    return VerificationCodeStore(redis)


def test_generate_email_code_is_six_digits():
    code = generate_email_code()

    assert len(code) == 6
    assert code.isdigit()


def test_hash_email_code_is_deterministic():
    assert hash_email_code("123456") == hash_email_code("123456")
    assert hash_email_code("123456") != hash_email_code("654321")


async def test_issue_then_verify_succeeds(store: VerificationCodeStore):
    code = await store.issue(PURPOSE_SIGNUP, "test@example.com")

    await store.verify(PURPOSE_SIGNUP, "test@example.com", code)  # 예외 없이 통과해야 함


async def test_verify_raises_when_code_missing(store: VerificationCodeStore):
    with pytest.raises(BadRequestException):
        await store.verify(PURPOSE_SIGNUP, "missing@example.com", "000000")


async def test_verify_raises_and_counts_attempts_on_wrong_code(store: VerificationCodeStore, redis):
    code = await store.issue(PURPOSE_SIGNUP, "test@example.com")
    wrong_code = "000000" if code != "000000" else "111111"

    with pytest.raises(BadRequestException):
        await store.verify(PURPOSE_SIGNUP, "test@example.com", wrong_code)

    raw = await redis.get(store._code_key(PURPOSE_SIGNUP, "test@example.com"))
    assert json.loads(raw)["attempts"] == 1


async def test_verify_deletes_code_after_max_attempts(store: VerificationCodeStore, redis):
    code = await store.issue(PURPOSE_SIGNUP, "test@example.com")
    wrong_code = "000000" if code != "000000" else "111111"

    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(BadRequestException):
            await store.verify(PURPOSE_SIGNUP, "test@example.com", wrong_code)

    assert await redis.get(store._code_key(PURPOSE_SIGNUP, "test@example.com")) is None


async def test_verify_consumes_code_so_it_cannot_be_reused(store: VerificationCodeStore):
    code = await store.issue(PURPOSE_SIGNUP, "test@example.com")
    await store.verify(PURPOSE_SIGNUP, "test@example.com", code)

    with pytest.raises(BadRequestException):
        await store.verify(PURPOSE_SIGNUP, "test@example.com", code)


async def test_resend_allows_only_once_per_cycle(store: VerificationCodeStore):
    await store.issue(PURPOSE_SIGNUP, "test@example.com")

    await store.resend(PURPOSE_SIGNUP, "test@example.com")  # 첫 재발송은 허용됨

    with pytest.raises(BadRequestException):
        await store.resend(PURPOSE_SIGNUP, "test@example.com")


async def test_issue_resets_resend_cooldown(store: VerificationCodeStore):
    await store.issue(PURPOSE_SIGNUP, "test@example.com")
    await store.resend(PURPOSE_SIGNUP, "test@example.com")

    # 새로운 인증 사이클이 시작되면 재발송 카운터도 초기화되어야 함
    await store.issue(PURPOSE_SIGNUP, "test@example.com")
    await store.resend(PURPOSE_SIGNUP, "test@example.com")  # 다시 재발송 가능해야 함
