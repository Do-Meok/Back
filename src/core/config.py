from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str = "domeok"

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: SecretStr
    PHONE_AES_KEY: SecretStr
    HMAC_SECRET: SecretStr

    OPENAI_API_KEY: SecretStr
    NAVER_OCR_SECRET_KEY: SecretStr
    NAVER_OCR_API_URL: SecretStr
    OCR_LLM_MODEL: str = "gpt-5-nano"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def rag_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/domeok_rag"
        )


@lru_cache  # get_settings()를 호출할 때마다 매번 파일/환경변수를 다시 읽는 연산 발생 억제
def get_settings() -> Settings:
    return Settings()


settings = Settings()
