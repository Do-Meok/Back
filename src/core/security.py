import hmac
import hashlib

from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from jose import jwt, JWTError

from core.config import settings
from domains.user.exceptions import TokenExpiredException, UnauthorizedException

JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = settings.JWT_SECRET_KEY.get_secret_value()

FERNET_KEY = settings.PHONE_AES_KEY.get_secret_value()
HMAC_SECRET = settings.HMAC_SECRET.get_secret_value()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
cipher_suite = Fernet(FERNET_KEY)
security_scheme = HTTPBearer(auto_error=False)


# --- 비밀번호 관련 ---
def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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


# --- JWT 토큰 관련 ---
def create_jwt(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=1),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt(access_token: str) -> str:
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise TokenExpiredException()
        return user_id

    except JWTError:
        return TokenExpiredException()


# --- 토큰 ---
def get_access_token(
    auth_header: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> str:
    if auth_header is None:
        raise UnauthorizedException()
    return auth_header.credentials
