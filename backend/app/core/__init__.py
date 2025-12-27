"""
Основные компоненты OSAGAMING CRM
Конфигурация, безопасность, база данных и другие core модули
"""

from .config import settings, get_settings
from .database import get_db, create_tables, drop_tables, check_database_connection
from .security import (
    security_manager, get_current_user, get_current_active_user,
    get_current_superuser, require_permissions
)
from .exceptions import (
    BusinessLogicException, DatabaseException,
    setup_exception_handlers, create_error_response
)
from .logging import (
    setup_logging, AppLogger, logger, auth_logger, 
    chat_logger, db_logger, security_logger
)
from .monitoring import (
    metrics, RequestMetricsMiddleware, get_metrics,
    generate_prometheus_metrics, comprehensive_health_check,
    performance_tracker
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    
    # Database
    "get_db",
    "create_tables",
    "drop_tables", 
    "check_database_connection",
    
    # Security
    "security_manager",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "require_permissions",
    
    # Exceptions
    "BusinessLogicException",
    "DatabaseException",
    "setup_exception_handlers",
    "create_error_response",
    
    # Logging
    "setup_logging",
    "AppLogger",
    "logger",
    "auth_logger",
    "chat_logger", 
    "db_logger",
    "security_logger",
    
    # Monitoring
    "metrics",
    "RequestMetricsMiddleware",
    "get_metrics",
    "generate_prometheus_metrics",
    "comprehensive_health_check",
    "performance_tracker"
]