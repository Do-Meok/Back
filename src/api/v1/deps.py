from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_redis
from core.security import get_access_token, REFRESH_TOKEN_EXPIRE_SECONDS
from domains.assistant.llm_handler import LLMHandler
from domains.assistant.service import AssistantService
from domains.auth.refresh_store import RefreshTokenStore
from domains.auth.service import AuthService
from domains.ingredient.repository import IngredientRepository
from domains.ingredient.service import IngredientService
from domains.recipe.repository import RecipeRepository
from domains.recipe.service import RecipeService
from domains.user.model import User
from domains.user.repository import UserRepository
from domains.user.service import UserService


# --- 유저 관련 DI ---
def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)

def get_refresh_store() -> RefreshTokenStore:
    return RefreshTokenStore(get_redis(), ttl_seconds=REFRESH_TOKEN_EXPIRE_SECONDS)

def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
    refresh_store: RefreshTokenStore = Depends(get_refresh_store),
) -> UserService:
    return UserService(user_repo=user_repo, refresh_store=refresh_store)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo), redis: Redis = Depends(get_redis)
) -> AuthService:
    return AuthService(user_repo=user_repo, redis=redis)


async def get_current_user(
    access_token: str = Depends(get_access_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return await auth_service.get_user_by_token(access_token)

"""
async def get_social_auth_service(
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SocialAuthService:
    user_repo = UserRepository(session)
    return SocialAuthService(user_repo, redis)
"""

# --- 재료 관련 DI ---
def get_ingredient_repo(
    session: AsyncSession = Depends(get_db),
) -> IngredientRepository:
    return IngredientRepository(session)


def get_ingredient_service(
    user: User = Depends(get_current_user),
    ingredient_repo: IngredientRepository = Depends(get_ingredient_repo),
) -> IngredientService:
    return IngredientService(user=user, ingredient_repo=ingredient_repo)


# --- Assistant 관련 ---
async def get_llm_handler() -> LLMHandler:
    return LLMHandler()


async def get_assistant_service(
    user: User = Depends(get_current_user),
    ingredient_repo: IngredientRepository = Depends(get_ingredient_repo),
    llm_handler: LLMHandler = Depends(get_llm_handler),
    redis: Redis = Depends(get_redis),
) -> AssistantService:
    return AssistantService(user=user, ingredient_repo=ingredient_repo, llm_handler=llm_handler, redis=redis)


# --- 레시피 관련 DI ---
def get_recipe_repo(
    session: AsyncSession = Depends(get_db),
) -> RecipeRepository:
    return RecipeRepository(session)


def get_recipe_service(
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    user: User = Depends(get_current_user),
) -> RecipeService:
    return RecipeService(user=user, recipe_repo=recipe_repo)
