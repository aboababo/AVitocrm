"""
Настройка логирования OSAGAMING CRM
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class AppLogger:
    """Класс для логирования с контекстом приложения"""
    
    def __init__(self, name: str = "osagaming"):
        self.name = name
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка базового логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def get_logger(self, module: str) -> logging.Logger:
        """Получение логгера для конкретного модуля"""
        return logging.getLogger(f"{self.name}.{module}")


# Глобальные логгеры
logger = AppLogger().get_logger("app")
auth_logger = AppLogger().get_logger("auth")
chat_logger = AppLogger().get_logger("chat")
db_logger = AppLogger().get_logger("database")
security_logger = AppLogger().get_logger("security")


def setup_logging():
    """Инициализация логирования"""
    pass  # Логгеры уже инициализированы при импорте