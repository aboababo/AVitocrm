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

# Дополнительные роутеры
try:
    from app.api.v1.listings import router as listings_router
    api_router.include_router(listings_router, prefix="/listings", tags=["listings"])
except ImportError:
    pass

try:
    from app.api.v1.deliveries import router as deliveries_router
    api_router.include_router(deliveries_router, prefix="/deliveries", tags=["deliveries"])
except ImportError:
    pass

try:
    from app.api.v1.settings import router as settings_router
    api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
except ImportError:
    pass

try:
    from app.api.v1.quick_replies import router as quick_replies_router
    api_router.include_router(quick_replies_router, prefix="/quick-replies", tags=["quick-replies"])
except ImportError:
    pass