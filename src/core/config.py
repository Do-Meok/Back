from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True)

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


settings = Settings()  # 유효성 체크
