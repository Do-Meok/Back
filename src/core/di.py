from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from core.security import get_access_token
from core.database import get_db, get_redis
from domains.assistant.llm_handler import LLMHandler
from domains.assistant.service import AssistantService

from domains.ingredient.repository import IngredientRepository
from domains.ingredient.service import IngredientService
from domains.recipe.repository import RecipeRepository
from domains.recipe.service import RecipeService
from domains.refrigerator.repository import RefrigeratorRepository
from domains.refrigerator.service import RefrigeratorService
from domains.shopping.repository import ShoppingRepository
from domains.shopping.service import ShoppingService
from domains.user.repository import UserRepository
from domains.user.service import UserService
from domains.user.models import User


# --- 유저 관련 DI ---
def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_user_service(session: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)) -> UserService:
    repo = UserRepository(session)
    return UserService(user_repo=repo, redis=redis)


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
    return AssistantService(user=user, ingredient_repo=ingredient_repo, llm_handler=llm_handler)


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


# --- 장보기 관련 DI ---
def get_shopping_repo(
    session: AsyncSession = Depends(get_db),
) -> ShoppingRepository:
    return ShoppingRepository(session)


def get_shopping_service(
    shopping_repo: ShoppingRepository = Depends(get_shopping_repo),
    user: User = Depends(get_current_user),
) -> ShoppingService:
    return ShoppingService(user=user, shopping_repo=shopping_repo)


# --- 냉장고 관련 DI ---
def get_refrigerator_repo(
    session: AsyncSession = Depends(get_db),
) -> RefrigeratorRepository:
    return RefrigeratorRepository(session)


def get_refrigerator_service(
    refrigerator_repo: RefrigeratorRepository = Depends(get_refrigerator_repo),
    user: User = Depends(get_current_user),
) -> RefrigeratorService:
    return RefrigeratorService(user=user, refrigerator_repo=refrigerator_repo)
