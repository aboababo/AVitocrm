"""
Простая конфигурация приложения без pydantic
"""

import os
import sqlite3
import json
from functools import lru_cache
from typing import List, Optional


def get_avito_keys_from_db() -> dict:
    """Получение ключей Avito API из базы данных"""
    db_paths = ['osagaming_crm.db', 'crm.db']
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Проверка наличия таблицы system_settings
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'")
                if cursor.fetchone():
                    cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE '%avito%'")
                    settings = cursor.fetchall()
                    
                    avito_keys = {}
                    for setting in settings:
                        key, value = setting
                        avito_keys[key] = value
                    
                    conn.close()
                    
                    if avito_keys:
                        return avito_keys
                else:
                    print("INFO: Таблица system_settings не найдена в базе данных")
                    
            except Exception as e:
                print(f"ERROR: Ошибка при получении ключей из {db_path}: {e}")
                continue
    
    return {}


class Settings:
    """Простые настройки приложения без pydantic"""
    
    def __init__(self):
        # Основные настройки
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "OSAGAMING CRM")
        self.VERSION = os.getenv("VERSION", "2.0.0")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "true").lower() == "true"
        
        # Безопасность
        self.SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.ALGORITHM = os.getenv("ALGORITHM", "HS256")
        
        # База данных
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./osagaming_crm.db")
        self.DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC", "sqlite+aiosqlite:///./osagaming_crm.db")
        
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
        
        # CORS - обрабатываем строку в список
        cors_origins = os.getenv("ALLOWED_HOSTS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000,localhost,127.0.0.1")
        self.ALLOWED_HOSTS = [host.strip() for host in cors_origins.split(",")]
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Pagination
        self.DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
        self.MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
        
        # Получение ключей Avito API из базы данных или .env
        avito_keys = get_avito_keys_from_db()
        
        self.AVITO_ACCESS_TOKEN = os.getenv("AVITO_ACCESS_TOKEN") or avito_keys.get('avito_access_token')
        self.AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID") or avito_keys.get('avito_client_id')
        self.AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET") or avito_keys.get('avito_client_secret')
        self.AVITO_WEBHOOK_URL = os.getenv("AVITO_WEBHOOK_URL") or avito_keys.get('avito_webhook_url') or "http://localhost:8000/api/v1/avito/webhook"
        
        # Обработка AVITO_WEBHOOK_TYPES из строки в список
        avito_webhook_types = os.getenv("AVITO_WEBHOOK_TYPES", "message,chat")
        self.AVITO_WEBHOOK_TYPES = [t.strip() for t in avito_webhook_types.split(",")]
        
        # Валидация секретного ключа
        if not self.SECRET_KEY or self.SECRET_KEY == "your-secret-key-here-change-in-production":
            if self.ENVIRONMENT == "production":
                raise ValueError("Секретный ключ должен быть изменен в production!")
    
        # Логирование статуса ключей Avito
        self._log_avito_status()
    
    def _log_avito_status(self):
        """Логирование статуса ключей Avito API"""
        has_token = bool(self.AVITO_ACCESS_TOKEN)
        has_client_id = bool(self.AVITO_CLIENT_ID)
        has_client_secret = bool(self.AVITO_CLIENT_SECRET)
        
        if has_token and has_client_id and has_client_secret:
            print("OK: Avito API ключи настроены")
        elif has_token:
            print("WARNING: Частичная настройка Avito API (есть токен, нет client credentials)")
        else:
            print("INFO: Avito API работает в демо-режиме (ключи не настроены)")
    
    @property
    def cors_origins(self) -> List[str]:
        """Получение CORS origins"""
        return self.ALLOWED_HOSTS

    @property
    def has_avito_keys(self) -> bool:
        """Проверка наличия всех необходимых ключей Avito API"""
        return bool(self.AVITO_ACCESS_TOKEN and self.AVITO_CLIENT_ID and self.AVITO_CLIENT_SECRET)

    @property
    def has_avito_token(self) -> bool:
        """Проверка наличия токена Avito API"""
        return bool(self.AVITO_ACCESS_TOKEN)


@lru_cache()
def get_settings() -> Settings:
    """Получение настроек (cached)"""
    return Settings()


# Глобальный экземпляр настроек
settings = Settings()