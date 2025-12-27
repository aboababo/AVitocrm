"""
Пользовательские исключения OSAGAMING CRM
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional


class BusinessLogicException(HTTPException):
    """Исключение для ошибок бизнес-логики"""
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class DatabaseException(HTTPException):
    """Исключение для ошибок базы данных"""
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)


def create_error_response(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Создание стандартизированного ответа об ошибке"""
    response = {
        "success": False,
        "error": {
            "message": message,
            "code": error_code or f"ERROR_{status_code}"
        }
    }
    if details:
        response["error"]["details"] = details
    return response


def setup_exception_handlers(app):
    """Настройка глобальных обработчиков исключений"""
    
    @app.exception_handler(BusinessLogicException)
    async def business_logic_exception_handler(request: Request, exc: BusinessLogicException):
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(
                status_code=exc.status_code,
                message=exc.detail,
                error_code="BUSINESS_LOGIC_ERROR"
            )
        )
    
    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request: Request, exc: DatabaseException):
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(
                status_code=exc.status_code,
                message=exc.detail,
                error_code="DATABASE_ERROR"
            )
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                status_code=500,
                message="Внутренняя ошибка сервера",
                error_code="INTERNAL_ERROR",
                details={"detail": str(exc)} if True else None
            )
        )