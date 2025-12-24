"""
OSAGAMING CRM - Вспомогательные функции для API
===============================================
"""

from typing import Any, Dict, Optional

from flask import request
from marshmallow import ValidationError as MarshmallowValidationError
from utils.exceptions import ValidationError
from utils.pagination import get_pagination_params, paginate_query
from utils.schemas import PaginationSchema


def validate_pagination() -> tuple[int, int]:
    """
    Валидация параметров пагинации из запроса

    Returns:
        tuple: (page, per_page)

    Raises:
        ValidationError: Если параметры невалидны
    """
    schema = PaginationSchema()
    try:
        data = schema.load(request.args.to_dict())
        return data["page"], data["per_page"]
    except MarshmallowValidationError as err:
        raise ValidationError("Ошибка валидации параметров пагинации", errors=err.messages)


def get_paginated_response(query: str, params: tuple = (), **kwargs) -> Dict[str, Any]:
    """
    Получить пагинированный ответ для SQL запроса

    Args:
        query: SQL запрос (без LIMIT/OFFSET)
        params: Параметры для запроса
        **kwargs: Дополнительные параметры для paginate_query

    Returns:
        dict: Пагинированный ответ
    """
    page, per_page = get_pagination_params(request)
    return paginate_query(query, params, page, per_page, **kwargs)


def validate_request_data(schema_class, data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Валидация данных запроса по схеме

    Args:
        schema_class: Класс схемы marshmallow
        data: Данные для валидации (если None, берется из request.json)

    Returns:
        dict: Валидированные данные

    Raises:
        ValidationError: Если данные невалидны
    """
    if data is None:
        data = request.get_json() or {}

    schema = schema_class()
    try:
        return schema.load(data)
    except MarshmallowValidationError as err:
        raise ValidationError("Ошибка валидации данных", errors=err.messages)
