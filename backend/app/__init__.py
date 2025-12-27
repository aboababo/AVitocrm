"""
OSAGAMING CRM - Современная архитектура
FastAPI Backend с микросервисной архитектурой
"""

from .main import app
from .core import (
    settings, get_settings, get_db, security_manager,
    BusinessLogicException, DatabaseException,
    setup_exception_handlers, setup_logging,
    metrics, performance_tracker
)

__version__ = "2.0.0"
__all__ = [
    "app",
    "settings",
    "get_settings", 
    "get_db",
    "security_manager",
    "BusinessLogicException",
    "DatabaseException",
    "setup_exception_handlers",
    "setup_logging",
    "metrics",
    "performance_tracker"
]