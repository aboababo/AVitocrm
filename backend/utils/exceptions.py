"""
OSAGAMING CRM - Классы исключений для обработки ошибок
=======================================================
"""

from typing import Any, Dict, Optional


class APIError(Exception):
    """Базовый класс для API ошибок"""

    def __init__(self, message: str, status_code: int = 400, error_code: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "API_ERROR"
        super().__init__(self.message)


class ValidationError(APIError):
    """Ошибка валидации данных"""

    def __init__(
        self,
        message: str = "Ошибка валидации данных",
        errors: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, 400, "VALIDATION_ERROR")
        self.errors = errors or {}


class NotFoundError(APIError):
    """Ресурс не найден"""

    def __init__(self, resource: str, resource_id: Optional[str] = None):
        message = f"{resource} не найден"
        if resource_id:
            message += f" (id: {resource_id})"
        super().__init__(message, 404, "NOT_FOUND")


class PermissionDeniedError(APIError):
    """Доступ запрещен"""

    def __init__(self, message: str = "Доступ запрещен"):
        super().__init__(message, 403, "PERMISSION_DENIED")


class AuthenticationError(APIError):
    """Ошибка аутентификации"""

    def __init__(self, message: str = "Неверный email или пароль"):
        super().__init__(message, 401, "AUTHENTICATION_ERROR")


class RateLimitError(APIError):
    """Превышен лимит запросов"""

    def __init__(self, message: str = "Превышен лимит запросов. Попробуйте позже"):
        super().__init__(message, 429, "RATE_LIMIT_EXCEEDED")
