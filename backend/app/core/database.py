"""
Настройка базы данных
Асинхронное подключение к БД с SQLAlchemy 2.0
"""

import os
import sqlite3
import logging
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker

# Настройка логирования
logger = logging.getLogger(__name__)

# Получаем настройки из config_simple
try:
    from app.core.config_simple import settings
except ImportError:
    # Fallback настройки если config_simple недоступен
    DATABASE_URL = "sqlite:///./crm.db"
    DATABASE_URL_ASYNC = "sqlite+aiosqlite:///./crm.db"
    DEBUG = False
else:
    DATABASE_URL = getattr(settings, 'DATABASE_URL', 'sqlite:///./crm.db')
    DATABASE_URL_ASYNC = getattr(settings, 'DATABASE_URL_ASYNC', 'sqlite+aiosqlite:///./crm.db')
    DEBUG = getattr(settings, 'DEBUG', False)

# Создание базового класса для моделей
Base = declarative_base()

# Метаданные для миграций
metadata = MetaData()

# Импорт моделей для их регистрации
try:
    from app.models import User, Chat, Message  # noqa
    logger.info("Models imported successfully")
except ImportError as e:
    logger.warning(f"Failed to import models: {e}")

# Асинхронный движок для production
async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)

# Создание session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# Синхронный движок для миграций и простых операций
sync_engine = create_engine(
    DATABASE_URL, 
    echo=DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)

# Создание session factory для миграций
SessionLocal = sessionmaker(bind=sync_engine, autoflush=True, autocommit=False)

# Для обратной совместимости
engine = sync_engine  # Используем sync_engine для тестов

# Dependency для FastAPI
async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Utility functions
async def create_tables():
    """Создание всех таблиц с fallback механизмом"""
    try:
        # Проверяем подключение к БД
        await check_database_connection()
        
        # Создаем таблицы
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
        # Создаем тестовые данные если БД пустая
        await create_initial_data()
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        # Пробуем fallback метод
        await create_tables_fallback()

async def create_tables_fallback():
    """Fallback метод создания таблиц через синхронный движок"""
    try:
        logger.info("Trying fallback table creation method")
        
        # Создаем таблицы через sync движок
        Base.metadata.create_all(bind=sync_engine)
        
        # Создаем тестовые данные
        create_initial_data_sync()
        
        logger.info("Database tables created via fallback method")
        
    except Exception as e:
        logger.error(f"Failed to create tables via fallback: {e}")
        raise

async def create_initial_data():
    """Создание начальных данных в БД"""
    try:
        from app.models import User, Chat, Message
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            # Проверяем есть ли уже пользователи
            result = await session.execute(select(User).limit(1))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info("Initial data already exists")
                return
            
            # Создаем тестового пользователя
            test_user = User(
                email="admin@osagaming.com",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8j1G1v7e1O",  # "password"
                first_name="Admin",
                last_name="User",
                full_name="Admin User",
                status="ACTIVE",
                is_active=True,
                is_superuser=True,
                is_verified=True,
                email_notifications=True,
                push_notifications=True
            )
            
            session.add(test_user)
            await session.commit()
            
            logger.info("Initial test user created")
            
    except Exception as e:
        logger.warning(f"Failed to create initial data: {e}")

def create_initial_data_sync():
    """Создание начальных данных через sync метод"""
    try:
        from app.models import User
        
        with SessionLocal() as session:
            # Проверяем есть ли уже пользователи
            existing_user = session.query(User).first()
            
            if existing_user:
                logger.info("Initial data already exists (sync)")
                return
            
            # Создаем тестового пользователя
            test_user = User(
                email="admin@osagaming.com",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8j1G1v7e1O",  # "password"
                first_name="Admin",
                last_name="User",
                full_name="Admin User",
                status="ACTIVE",
                is_active=True,
                is_superuser=True,
                is_verified=True,
                email_notifications=True,
                push_notifications=True
            )
            
            session.add(test_user)
            session.commit()
            
            logger.info("Initial test user created (sync)")
            
    except Exception as e:
        logger.warning(f"Failed to create initial data (sync): {e}")

async def drop_tables():
    """Удаление всех таблиц"""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise

def check_database_file_exists() -> bool:
    """Проверка существования файла базы данных"""
    db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
    return os.path.exists(db_path)

def create_database_directory():
    """Создание директории для базы данных если необходимо"""
    try:
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
            
    except Exception as e:
        logger.warning(f"Failed to create database directory: {e}")

# Health check для БД
async def check_database_connection() -> bool:
    """Проверка подключения к БД"""
    try:
        # Создаем директорию если необходимо
        create_database_directory()
        
        # Проверяем подключение
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False

def sync_check_database_connection() -> bool:
    """Синхронная проверка подключения к БД"""
    try:
        # Создаем директорию если необходимо
        create_database_directory()
        
        # Проверяем подключение через sync движок
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Sync database connection check failed: {e}")
        return False

def initialize_database():
    """Инициализация базы данных (синхронная)"""
    """Главная функция для инициализации БД при запуске"""
    logger.info("Initializing database...")
    
    try:
        # Создаем директорию для БД
        create_database_directory()
        
        # Проверяем подключение
        if not sync_check_database_connection():
            logger.error("Database connection failed")
            return False
        
        # Создаем таблицы
        Base.metadata.create_all(bind=sync_engine)
        
        # Создаем начальные данные
        create_initial_data_sync()
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

# Функция для проверки состояния БД
def get_database_status() -> dict:
    """Получение статуса базы данных"""
    status = {
        "connected": False,
        "tables_exist": False,
        "has_data": False,
        "file_exists": False,
        "path": None
    }
    
    try:
        # Проверяем существование файла
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        status["file_exists"] = os.path.exists(db_path)
        status["path"] = db_path
        
        # Проверяем подключение
        if sync_check_database_connection():
            status["connected"] = True
            
            # Проверяем наличие таблиц
            try:
                with SessionLocal() as session:
                    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                    tables = [row[0] for row in result.fetchall()]
                    status["tables_exist"] = len(tables) > 0
                    
                    # Проверяем наличие данных
                    if 'users' in tables:
                        result = session.execute(text("SELECT COUNT(*) FROM users"))
                        user_count = result.fetchone()[0]
                        status["has_data"] = user_count > 0
                        
            except Exception as e:
                logger.warning(f"Failed to check database tables/data: {e}")
                
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
    
    return status