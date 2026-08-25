# api/v1/api.py

from fastapi import APIRouter

from api.v1.endpoints import auth, user

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(user.router, prefix="/users", tags=["User"])