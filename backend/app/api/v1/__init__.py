"""
Главный API роутер для FastAPI
Объединение всех API endpoints
"""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.chats import router as chats_router
from app.api.v1.avito import router as avito_router

# Главный API роутер
api_router = APIRouter()

# Подключение роутеров
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(chats_router, prefix="/chats", tags=["chats"])
api_router.include_router(avito_router, prefix="/avito", tags=["avito"])