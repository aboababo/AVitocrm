"""
OSAGAMING CRM - Утилиты для пагинации
======================================
"""

from typing import Any, Dict, Tuple

from config import Config
from database import get_connection


def paginate_query(
    query: str,
    params: Tuple = (),
    page: int = 1,
    per_page: int = None,
    max_per_page: int = None,
) -> Dict[str, Any]:
    """
    Универсальная функция пагинации для SQL запросов

    Args:
        query: SQL запрос (без LIMIT/OFFSET)
        params: Параметры для запроса
        page: Номер страницы (начинается с 1)
        per_page: Количество элементов на странице
        max_per_page: Максимальное количество элементов

    Returns:
        dict: {
            'items': [...],
            'total': int,
            'page': int,
            'per_page': int,
            'pages': int,
            'has_next': bool,
            'has_prev': bool
        }
    """
    if per_page is None:
        per_page = Config.DEFAULT_PAGE_SIZE
    if max_per_page is None:
        max_per_page = Config.MAX_PAGE_SIZE

    # Ограничиваем per_page
    per_page = min(per_page, max_per_page)
    page = max(1, page)
    offset = (page - 1) * per_page

    # Работа с соединением через контекстный менеджер
    with get_connection() as conn:
        # Получаем общее количество
        # Убираем ORDER BY из запроса для подсчета
        count_query = query
        if "ORDER BY" in query.upper():
            count_query = query[: query.upper().index("ORDER BY")]

        count_query = f"SELECT COUNT(*) as count FROM ({count_query}) as subquery"
        total = conn.execute(count_query, params).fetchone()["count"]

        # Получаем данные с пагинацией
        paginated_query = f"{query} LIMIT ? OFFSET ?"
        items = conn.execute(paginated_query, params + (per_page, offset)).fetchall()

        pages = (total + per_page - 1) // per_page if total > 0 else 0

        return {
            "items": [dict(item) for item in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        }


def get_pagination_params(request) -> Tuple[int, int]:
    """
    Получить параметры пагинации из запроса

    Args:
        request: Flask request объект

    Returns:
        tuple: (page, per_page)
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", Config.DEFAULT_PAGE_SIZE, type=int)

    # Ограничиваем значения
    page = max(1, page)
    per_page = min(max(1, per_page), Config.MAX_PAGE_SIZE)

    return page, per_page
