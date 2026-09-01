from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.quota import DailyQuotaStore
from core.redis import get_redis
from core.security import REFRESH_TOKEN_EXPIRE_SECONDS, get_access_token
from domains.auth.email_service import EmailService
from domains.auth.refresh_store import RefreshTokenStore
from domains.auth.service import AuthService
from domains.auth.signup_pending_store import SignupPendingStore
from domains.auth.verification_store import VerificationCodeStore
from domains.ingredient.repository import IngredientRepository
from domains.ingredient.service import IngredientService
from domains.ocr.service import OcrService
from domains.rag.retriever import RecipeRetriever, get_recipe_retriever
from domains.rag.service import RagService
from domains.recipe_detail.cache import RecipeDetailCache
from domains.recipe_detail.crawler import RecipeCrawler
from domains.recipe_detail.service import RecipeDetailService
from domains.saved_recipe.repository import SavedRecipeRepository
from domains.saved_recipe.service import SavedRecipeService
from domains.user.model import User
from domains.user.repository import UserRepository
from domains.user.service import UserService

_recipe_crawler = RecipeCrawler()


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


def get_verification_store() -> VerificationCodeStore:
    return VerificationCodeStore(get_redis())


def get_signup_pending_store() -> SignupPendingStore:
    return SignupPendingStore(get_redis())


def get_daily_quota_store() -> DailyQuotaStore:
    return DailyQuotaStore(get_redis())


def get_email_service() -> EmailService:
    backend = "smtp" if settings.SMTP_HOST else "console"
    return EmailService(
        backend=backend,
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        smtp_password=settings.SMTP_PASSWORD.get_secret_value() if settings.SMTP_PASSWORD else None,
        smtp_from_email=settings.SMTP_FROM_EMAIL,
        smtp_from_name=settings.SMTP_FROM_NAME,
    )


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    refresh_store: RefreshTokenStore = Depends(get_refresh_store),
    verification_store: VerificationCodeStore = Depends(get_verification_store),
    email_service: EmailService = Depends(get_email_service),
    signup_pending_store: SignupPendingStore = Depends(get_signup_pending_store),
    daily_quota_store: DailyQuotaStore = Depends(get_daily_quota_store),
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        refresh_store=refresh_store,
        verification_store=verification_store,
        email_service=email_service,
        signup_pending_store=signup_pending_store,
        daily_quota_store=daily_quota_store,
    )


async def get_current_user(
    access_token: str = Depends(get_access_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return await auth_service.get_user_by_token(access_token)


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


# --- RAG 관련 DI ---
def get_rag_retriever() -> RecipeRetriever:
    return get_recipe_retriever()


def get_rag_service(
    user: User = Depends(get_current_user),
    ingredient_repo: IngredientRepository = Depends(get_ingredient_repo),
    retriever: RecipeRetriever = Depends(get_rag_retriever),
    daily_quota_store: DailyQuotaStore = Depends(get_daily_quota_store),
) -> RagService:
    return RagService(
        user=user,
        ingredient_repo=ingredient_repo,
        retriever=retriever,
        daily_quota_store=daily_quota_store,
    )


# --- 레시피 관련(RAG, 레시피 저장) DI ---
def get_recipe_detail_service(
    user: User = Depends(get_current_user),
) -> RecipeDetailService:
    cache = RecipeDetailCache(get_redis(), ttl_seconds=86400)
    return RecipeDetailService(crawler=_recipe_crawler, cache=cache)


def get_saved_recipe_repo(
    session: AsyncSession = Depends(get_db),
) -> SavedRecipeRepository:
    return SavedRecipeRepository(session)


def get_saved_recipe_service(
    user: User = Depends(get_current_user),
    repo: SavedRecipeRepository = Depends(get_saved_recipe_repo),
    recipe_detail_service: RecipeDetailService = Depends(get_recipe_detail_service),
) -> SavedRecipeService:
    return SavedRecipeService(
        user=user,
        repo=repo,
        recipe_detail_service=recipe_detail_service,
    )


# OCR 관련 DI


def get_ocr_service(
    user: User = Depends(get_current_user),
) -> OcrService:
    return OcrService(
        api_url=settings.NAVER_OCR_API_URL.get_secret_value(),
        secret_key=settings.NAVER_OCR_SECRET_KEY.get_secret_value(),
        openai_api_key=settings.OPENAI_API_KEY.get_secret_value(),
        llm_model=settings.OCR_LLM_MODEL,
        user_id=user.id,
    )
