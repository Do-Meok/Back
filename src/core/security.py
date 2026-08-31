import hashlib
import hmac
import secrets
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from core.config import settings
from core.exception.exceptions import (
    InvalidTokenException,
    TokenExpiredException,
    UnAuthorizedException,
)
from core.timezone import KST

# 설정 및 상수
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30분
REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 14  # 14일
KAKAO_SIGNUP_TOKEN_EXPIRE_MINUTES = 10
KAKAO_SIGNUP_PURPOSE = "kakao_signup"
JWT_SECRET_KEY = settings.JWT_SECRET_KEY.get_secret_value()
JWT_ALGORITHM = "HS256"
FERNET_KEY = settings.PHONE_AES_KEY.get_secret_value()
HMAC_SECRET = settings.HMAC_SECRET.get_secret_value()

# 인스턴스 초기화
password_hasher = PasswordHash((Argon2Hasher(),))
security_scheme = HTTPBearer(auto_error=False)
cipher_suite = Fernet(FERNET_KEY.encode("utf-8"))


# --- 비밀번호 관련 ---
def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


# --- 전화번호 암호화 (양방향) ---
def encrypt_phone(plain_phone: str) -> str:
    return cipher_suite.encrypt(plain_phone.encode("UTF-8")).decode("UTF-8")


def decrypt_phone(encrypted_phone: str) -> str:
    return cipher_suite.decrypt(encrypted_phone.encode("UTF-8")).decode("UTF-8")


# --- 전화번호 해싱 (검색용/단방향) ---
def make_phone_hash(phone: str) -> str:
    mac = hmac.new(
        HMAC_SECRET.encode("UTF-8"),
        phone.encode("UTF-8"),
        hashlib.sha256,
    ).digest()
    return urlsafe_b64encode(mac).decode("UTF-8")


# --- 토큰 관련 ---
def create_jwt(user_id: uuid.UUID) -> str:
    now = datetime.now(KST)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt(access_token: str) -> str:
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise TokenExpiredException("유효하지 않은 토큰입니다.")
        return user_id

    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredException() from e
    except jwt.PyJWTError as e:
        raise InvalidTokenException() from e


def create_kakao_signup_token(kakao_id: str) -> str:
    now = datetime.now(KST)
    payload = {
        "sub": kakao_id,
        "purpose": KAKAO_SIGNUP_PURPOSE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=KAKAO_SIGNUP_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_kakao_signup_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("purpose") != KAKAO_SIGNUP_PURPOSE:
            raise InvalidTokenException(detail="유효하지 않은 가입 토큰입니다.")
        kakao_id = payload.get("sub")
        if not kakao_id:
            raise InvalidTokenException(detail="유효하지 않은 가입 토큰입니다.")
        return str(kakao_id)
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredException(detail="가입 토큰이 만료되었습니다.") from e
    except jwt.PyJWTError as e:
        raise InvalidTokenException(detail="유효하지 않은 가입 토큰입니다.") from e


def create_refresh_token() -> str:
    return secrets.token_hex(32)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_access_token(
    auth_header: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> str:
    if auth_header is None:
        raise UnAuthorizedException()
    return auth_header.credentials
