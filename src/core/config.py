from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str = "domeok"
    REDIS_URL: str

    JWT_SECRET_KEY: SecretStr
    PHONE_AES_KEY: SecretStr
    HMAC_SECRET: SecretStr

    OPENAI_API_KEY: SecretStr

    NAVER_OCR_SECRET_KEY: SecretStr
    NAVER_OCR_API_URL: str

    KAKAO_REST_API_KEY: str
    KAKAO_REDIRECT_URI: str
    KAKAO_CLIENT_SECRET: SecretStr

    UNSPLASH_ACCESS_KEY: str
    UNSPLASH_SECRET_KEY: SecretStr

    @property
    def POSTGRES_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,  # 대소문자 구분
    )


settings = Settings()  # 유효성 체크
