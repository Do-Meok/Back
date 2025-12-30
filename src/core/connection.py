from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.config import settings


POSTGRES_DATABASE_URL = settings.POSTGRES_DATABASE_URL
postgres_engine = create_async_engine(POSTGRES_DATABASE_URL)
AsyncSession = sessionmaker(
    bind=postgres_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession
)

async def get_postgres_db():
    async with AsyncSession() as session:
        yield session