import hmac
import hashlib

from fastapi import Request
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

from core.config import settings
from domains.user.exceptions import (
    DuplicateEmailException,
    DuplicateNicknameException,
    InvalidCheckedPasswordException,
    DuplicatePhoneNumException,
    InvalidCredentialsException,
    TokenExpiredException,
)
from domains.user.repository import UserRepository
from domains.user.schemas import SignUpRequest, LogInRequest, LogInResponse
from domains.user.models import User

TEMP_AES_KEY = Fernet.generate_key()
TEMP_HMAC_SECRET = settings.HMAC_SECRET.get_secret_value()


class UserService:
    encoding = "UTF-8"
    secret_key = settings.JWT_SECRET_KEY.get_secret_value()
    jwt_algorithm = "HS256"

    # 비밀번호 해쉬 설정 (passlib - Argon2)
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    # 전화번호 암호화 설정 (Fernet - 양방향)
    cipher_suite = Fernet(TEMP_AES_KEY)

    # 전화번호 해싱 키 (HMAC - 단방향)
    phone_secret = TEMP_HMAC_SECRET

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    # --- 비밀번호 관련 ---
    def hash_password(self, plain_password: str) -> str:
        return self.pwd_context.hash(plain_password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    # --- 전화번호 관련 ---
    def _encrypt_phone(self, plain_phone: str) -> str:
        return self.cipher_suite.encrypt(plain_phone.encode(self.encoding)).decode(
            self.encoding
        )

    def decrypt_phone(self, encrypted_phone: str) -> str:
        return self.cipher_suite.decrypt(encrypted_phone.encode(self.encoding)).decode(
            self.encoding
        )

    def _make_phone_hash(self, phone: str) -> str:
        mac = hmac.new(
            self.phone_secret.encode(self.encoding),
            phone.encode(self.encoding),
            hashlib.sha256,
        ).digest()
        return urlsafe_b64encode(mac).decode(self.encoding)

    # --- JWT 토큰 관련 ---
    def create_jwt(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(days=1),
        }
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.jwt_algorithm,
        )

    def decode_jwt(self, access_token: str) -> str:
        try:
            payload = jwt.decode(
                access_token, self.secret_key, algorithms=[self.jwt_algorithm]
            )
            email = payload.get("sub")

            if email is None:
                raise TokenExpiredException()
            return email

        except JWTError:
            raise TokenExpiredException()

    # --- 로직 ---
    async def sign_up(self, request: SignUpRequest):
        try:
            # 이메일 중복 예외처리
            if await self.user_repo.get_user_by_email(request.email):
                raise DuplicateEmailException()

            # 닉네임 중복 예외처리
            if await self.user_repo.get_user_by_nickname(request.nickname):
                raise DuplicateNicknameException()

            # 비밀번호와 비밀번호 확인이 일치하지 않을 시
            if request.password != request.checked_password:
                raise InvalidCheckedPasswordException()

            # 전화번호 처리 로직
            phone_hash = None
            encrypted_phone = None

            if request.phone_num:
                phone_hash = self._make_phone_hash(request.phone_num)

                if await self.user_repo.get_user_by_phone_num(phone_hash):
                    raise DuplicatePhoneNumException()

                encrypted_phone = self._encrypt_phone(request.phone_num)

            hashed_password = self.hash_password(request.password)

            user = User(
                email=request.email,
                password=hashed_password,
                nickname=request.nickname,
                name=request.name,
                birth=request.birth,
                phone=encrypted_phone,
                phone_hash=phone_hash,
            )
            saved_user = await self.user_repo.save_user(user)
            return saved_user

        except Exception as e:
            raise e

    async def log_in(self, request: LogInRequest, req: Request):
        try:
            user = await self.user_repo.get_user_by_email(email=request.email)

            if not user or not self.verify_password(request.password, user.password):
                raise InvalidCredentialsException()

            access_token = self.create_jwt(user_id=user.id)
            return LogInResponse(access_token=access_token)

        except InvalidCredentialsException:
            raise

        except Exception as e:
            raise e
