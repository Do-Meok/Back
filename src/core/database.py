from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.config import settings


POSTGRES_DATABASE_URL = settings.POSTGRES_DATABASE_URL

# 엔진 생성
postgres_engine = create_async_engine(POSTGRES_DATABASE_URL)

# 세션 팩토리 생성
AsyncSession = sessionmaker(
    bind=postgres_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)

Base = declarative_base()


async def get_postgres_db():
    async with AsyncSession() as session:
        yield session
