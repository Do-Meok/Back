import uuid
from datetime import datetime, timedelta

import jwt
import pytest

from core import security
from core.exception.exceptions import InvalidTokenException, TokenExpiredException
from core.timezone import KST


def test_hash_and_verify_password_roundtrip():
    hashed = security.hash_password("password123")
    assert hashed != "password123"
    assert security.verify_password("password123", hashed)
    assert not security.verify_password("wrong-password", hashed)


def test_encrypt_and_decrypt_phone_roundtrip():
    encrypted = security.encrypt_phone("010-1234-5678")
    assert encrypted != "010-1234-5678"
    assert security.decrypt_phone(encrypted) == "010-1234-5678"


def test_make_phone_hash_is_deterministic_and_distinct():
    first = security.make_phone_hash("010-1234-5678")
    second = security.make_phone_hash("010-1234-5678")
    other = security.make_phone_hash("010-0000-0000")

    assert first == second
    assert first != other


def test_create_and_decode_jwt_roundtrip():
    user_id = uuid.uuid4()
    token = security.create_jwt(user_id)

    assert security.decode_jwt(token) == str(user_id)


def test_decode_jwt_raises_when_expired():
    now = datetime.now(KST)
    payload = {
        "sub": str(uuid.uuid4()),
        "iat": int((now - timedelta(minutes=40)).timestamp()),
        "exp": int((now - timedelta(minutes=10)).timestamp()),
    }
    expired_token = jwt.encode(payload, security.JWT_SECRET_KEY, algorithm=security.JWT_ALGORITHM)

    with pytest.raises(TokenExpiredException):
        security.decode_jwt(expired_token)


def test_decode_jwt_raises_when_tampered():
    token = security.create_jwt(uuid.uuid4())

    with pytest.raises(InvalidTokenException):
        security.decode_jwt(token + "tampered")


def test_create_and_decode_kakao_signup_token_roundtrip():
    token = security.create_kakao_signup_token("kakao-123")

    assert security.decode_kakao_signup_token(token) == "kakao-123"


def test_decode_kakao_signup_token_rejects_wrong_purpose():
    now = datetime.now(KST)
    payload = {
        "sub": "kakao-123",
        "purpose": "not_kakao_signup",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    token = jwt.encode(payload, security.JWT_SECRET_KEY, algorithm=security.JWT_ALGORITHM)

    with pytest.raises(InvalidTokenException):
        security.decode_kakao_signup_token(token)


def test_decode_kakao_signup_token_rejects_expired_token():
    now = datetime.now(KST)
    payload = {
        "sub": "kakao-123",
        "purpose": security.KAKAO_SIGNUP_PURPOSE,
        "iat": int((now - timedelta(minutes=20)).timestamp()),
        "exp": int((now - timedelta(minutes=1)).timestamp()),
    }
    token = jwt.encode(payload, security.JWT_SECRET_KEY, algorithm=security.JWT_ALGORITHM)

    with pytest.raises(TokenExpiredException):
        security.decode_kakao_signup_token(token)


def test_create_refresh_token_and_hash_are_deterministic():
    raw_token = security.create_refresh_token()

    assert security.hash_refresh_token(raw_token) == security.hash_refresh_token(raw_token)
    assert security.hash_refresh_token(raw_token) != raw_token
