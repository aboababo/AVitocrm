"""
Конфигурация приложения
Централизованное управление настройками с валидацией
"""

import os
from functools import lru_cache
from typing import List, Optional, Union

# Пробуем импортировать pydantic_settings, если недоступно - используем простые переменные
try:
    from pydantic_settings import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseSettings = object


class Settings(BaseSettings):
    """Настройки приложения с поддержкой .env файлов"""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Позволяет добавлять дополнительные поля из .env
    
    # Основные настройки
    PROJECT_NAME: str = "OSAGAMING CRM"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Безопасность
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # База данных
    DATABASE_URL: str = "sqlite:///./crm.db"
    DATABASE_URL_ASYNC: str = "sqlite+aiosqlite:///./crm.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 минут
    
    # CORS
    ALLOWED_HOSTS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # Avito API
    AVITO_ACCESS_TOKEN: Optional[str] = None
    AVITO_CLIENT_ID: Optional[str] = None
    AVITO_CLIENT_SECRET: Optional[str] = None
    AVITO_WEBHOOK_URL: Optional[str] = None
    AVITO_WEBHOOK_TYPES: str = "message,chat"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Обработка ALLOWED_HOSTS из строки в список
        if hasattr(self, 'ALLOWED_HOSTS') and isinstance(self.ALLOWED_HOSTS, str):
            self.ALLOWED_HOSTS = [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
        
        # Обработка AVITO_WEBHOOK_TYPES из строки в список
        if hasattr(self, 'AVITO_WEBHOOK_TYPES') and isinstance(self.AVITO_WEBHOOK_TYPES, str):
            self.AVITO_WEBHOOK_TYPES = [t.strip() for t in self.AVITO_WEBHOOK_TYPES.split(",")]
        
        # Валидация секретного ключа
        if not self.SECRET_KEY or self.SECRET_KEY == "your-secret-key-here-change-in-production":
            if self.ENVIRONMENT == "production":
                raise ValueError("Секретный ключ должен быть изменен в production!")
    
    @property
    def cors_origins(self) -> List[str]:
        """Получение CORS origins"""
        return self.ALLOWED_HOSTS if isinstance(self.ALLOWED_HOSTS, list) else [self.ALLOWED_HOSTS]


@lru_cache()
def get_settings() -> Settings:
    """Получение настроек (cached)"""
    return Settings()


# Глобальный экземпляр настроек
settings = get_settings()