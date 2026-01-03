from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from domains.user.repository import UserRepository
from domains.user.service import UserService
from core.connection import get_postgres_db

# --- 유저 관련 DI ---
def get_user_repo(session: AsyncSession = Depends(get_postgres_db)) -> UserRepository:
    return UserRepository(session)

def get_user_service(user_repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(user_repo)