from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

POSTGRES_DATABASE_URL = settings.POSTGRES_DATABASE_URL

engine = create_async_engine(
    POSTGRES_DATABASE_URL,
    echo=True,  # 개발 중에는 쿼리 로그 보기
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        yield session
