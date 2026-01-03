# api/v1/api.py

from fastapi import APIRouter
from api.v1.endpoints import user

api_router = APIRouter()

api_router.include_router(user.router, prefix="/users", tags=["User"])
# api_router.include_router(ingredient.router, prefix="/ingredients", tags=["ingredients"])
# api_router.include_router(recipe.router, prefix="/recipes", tags=["recipes"])