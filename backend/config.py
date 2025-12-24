"""
OSAGAMING CRM - Конфигурация приложения
========================================

Централизованная конфигурация через переменные окружения
"""

import os


class Config:
    """Конфигурация приложения"""

    # Базовые настройки
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # База данных
    DATABASE_PATH = os.getenv("DATABASE_PATH", "osagaming_crm.db")

    # Сессии
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS", "7"))
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_HTTPONLY = True

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

    # Rate Limiting
    RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", "memory://")
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per day, 50 per hour")
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5 per minute")

    # Avito API
    AVITO_API_BASE_URL = os.getenv("AVITO_API_BASE_URL", "https://api.avito.ru")

    # Логирование
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10240000"))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "10"))

    # Безопасность
    PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_TIME = int(os.getenv("LOGIN_LOCKOUT_TIME", "300"))  # секунды

    # Пагинация
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # Кэширование
    CACHE_TTL_STATS = int(os.getenv("CACHE_TTL_STATS", "60"))
    CACHE_TTL_CHATS = int(os.getenv("CACHE_TTL_CHATS", "30"))
    CACHE_TTL_SHOPS = int(os.getenv("CACHE_TTL_SHOPS", "300"))
    CACHE_TTL_USERS = int(os.getenv("CACHE_TTL_USERS", "300"))
    CACHE_TTL_SETTINGS = int(os.getenv("CACHE_TTL_SETTINGS", "600"))
    CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_DEFAULT", "60"))
