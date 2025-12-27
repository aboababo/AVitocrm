"""
OSAGAMING CRM - FastAPI Backend Application
Модульная архитектура с современными практиками разработки
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.api import api_router

# Временные импорты для быстрого запуска
from app.core.config_simple import settings
from app.core.database import initialize_database, get_database_status
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Starting OSAGAMING CRM Backend")
    
    # Инициализация базы данных
    db_status = get_database_status()
    logger.info(f"Database status: {db_status}")
    
    if not db_status['connected']:
        logger.warning("Database not connected, attempting initialization...")
        
        # Попытка инициализации
        if initialize_database():
            logger.info("Database initialized successfully")
        else:
            logger.error("Failed to initialize database")
    
    # Создание таблиц в БД (если не созданы)
    try:
        from app.core.database import create_tables
        await create_tables()
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.warning(f"Database table creation failed: {e}")
    
    # Инициализация дополнительных сервисов
    await init_services()
    
    yield
    
    # Shutdown
    logger.info("Shutting down OSAGAMING CRM Backend")
    await cleanup_resources()


# Создание FastAPI приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Современная CRM система для Avito продавцов",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка доверенных хостов (отключено для работы с Docker)
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=settings.ALLOWED_HOSTS
# )

# Временные middleware для базовой работы - удален, так как используется CORSMiddleware

# Подключение API роутеров
app.include_router(api_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Проверка состояния приложения"""
    from app.core.database import check_database_connection
    
    db_status = get_database_status()
    
    return {
        "status": "healthy",
        "timestamp": "2025-12-26T15:00:00Z",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "connected": db_status['connected'],
            "tables_exist": db_status['tables_exist'],
            "has_data": db_status['has_data'],
            "file_exists": db_status['file_exists']
        },
        "avito": {
            "has_credentials": settings.has_avito_keys,
            "has_token": settings.has_avito_token
        }
    }

# Database status endpoint
@app.get("/database/status")
async def database_status():
    """Получение детального статуса базы данных"""
    status = get_database_status()
    return {
        "database": status,
        "message": "Database is ready for use" if status['connected'] and status['tables_exist'] else "Database needs initialization"
    }

# Database initialize endpoint (для отладки)
@app.post("/database/initialize")
async def initialize_database_endpoint():
    """Инициализация базы данных через API"""
    try:
        if initialize_database():
            return {"status": "success", "message": "Database initialized successfully"}
        else:
            return {"status": "error", "message": "Failed to initialize database"}
    except Exception as e:
        return {"status": "error", "message": f"Database initialization error: {str(e)}"}

# Metrics endpoint для мониторинга
@app.get("/metrics")
async def metrics():
    """Метрики для Prometheus"""
    db_status = get_database_status()
    return {
        "status": "ok",
        "database_connected": db_status['connected'],
        "database_tables": db_status['tables_exist'],
        "database_data": db_status['has_data'],
        "avito_configured": settings.has_avito_keys,
        "environment": settings.ENVIRONMENT
    }


async def init_services():
    """Инициализация дополнительных сервисов при старте"""
    logger.info("Initializing additional services")
    
    # Проверяем подключение к БД
    db_status = get_database_status()
    if db_status['connected']:
        logger.info("Database services ready")
    else:
        logger.warning("Database services not ready")
    
    # Инициализация Redis подключения (если настроен)
    # Инициализация очередей
    # Инициализация кэша
    # Инициализация Avito сервиса
    try:
        from app.services.avito_service import avito_client
        logger.info(f"Avito client ready - has credentials: {avito_client.has_credentials()}")
    except Exception as e:
        logger.warning(f"Avito client initialization failed: {e}")


async def cleanup_resources():
    """Очистка ресурсов при остановке"""
    logger.info("Cleaning up resources")
    # Закрытие подключений к БД
    # Очистка кэша
    # Остановка воркеров


if __name__ == "__main__":
    import uvicorn
    
    # Инициализация БД при прямом запуске
    logger.info("Initializing database on direct startup...")
    initialize_database()
    
    # Запускаем Uvicorn напрямую с объектом `app` — это надёжнее при запуске как скрипт
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )