from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_access_token
from core.database import get_db
from domains.assistant.llm_handler import LLMHandler
from domains.assistant.service import AssistantService

from domains.ingredient.repository import IngredientRepository
from domains.ingredient.service import IngredientService
from domains.user.repository import UserRepository
from domains.user.service import UserService
from domains.user.models import User


# --- 유저 관련 DI ---
def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_user_service(user_repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(user_repo)


async def get_current_user(
    req: Request,
    access_token: str = Depends(get_access_token),
    user_service: UserService = Depends(get_user_service),
) -> User:
    return await user_service.get_user_by_token(access_token, req)


# --- 재료 관련 DI ---
def get_ingredient_repo(
    session: AsyncSession = Depends(get_db),
) -> IngredientRepository:
    return IngredientRepository(session)


def get_ingredient_service(
    ingredient_repo: IngredientRepository = Depends(get_ingredient_repo),
    user: User = Depends(get_current_user),
) -> IngredientService:
    return IngredientService(user=user, ingredient_repo=ingredient_repo)


# --- Assistant 관련 ---
async def get_llm_handler() -> LLMHandler:
    return LLMHandler()


async def get_assistant_service(
    user: User = Depends(get_current_user),
    ingredient_repo: IngredientRepository = Depends(get_ingredient_repo),
    llm_handler: LLMHandler = Depends(get_llm_handler),
) -> AssistantService:
    return AssistantService(
        user=user, ingredient_repo=ingredient_repo, llm_handler=llm_handler
    )
