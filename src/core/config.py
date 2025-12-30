from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"  # 기본값 설정 (없으면 로컬로 간주)
    DB_PORT: int = 5432
    DB_NAME: str = "domeok"

    @property
    def POSTGRES_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",  # 정의되지 않은 변수는 무시
        case_sensitive=True  # 대소문자 구분 (기존 class Config에 있던 것 이동)
    )

settings = Settings()  # 유효성 체크