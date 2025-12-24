"""
OSAGAMING CRM - Построитель оптимизированных запросов
======================================================

Утилиты для построения оптимизированных SQL запросов
"""

from typing import Optional, Tuple


def build_chats_query(
    show_pool: bool = False,
    include_completed: bool = True,
    updated_since: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    has_name_columns: bool = True,
) -> Tuple[str, Tuple]:
    """
    Построить оптимизированный запрос для получения чатов

    Args:
        show_pool: Показывать только чаты без менеджера
        include_completed: Включать завершенные чаты
        updated_since: Фильтр по времени обновления
        limit: Лимит результатов
        offset: Смещение для пагинации
        has_name_columns: Наличие колонок first_name/last_name

    Returns:
        tuple: (SQL запрос, параметры)
    """
    # Базовый SELECT с JOIN
    name_field = (
        "COALESCE(NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''), u.username, '')"
        if has_name_columns
        else "COALESCE(u.username, '')"
    )

    base_query = f"""
        SELECT 
            c.*, 
            s.name as shop_name,
            {name_field} as assigned_manager_name,
            CASE 
                WHEN s.client_id IS NOT NULL AND s.client_secret IS NOT NULL AND s.user_id IS NOT NULL 
                THEN 1 ELSE 0 
            END AS has_avito_creds,
            CASE 
                WHEN s.client_id IS NOT NULL AND s.client_secret IS NOT NULL AND s.user_id IS NOT NULL 
                THEN 'ok' ELSE 'missing' 
            END AS avito_credentials_status,
            s.webhook_registered
        FROM avito_chats c
        LEFT JOIN avito_shops s ON c.shop_id = s.id
        LEFT JOIN users u ON c.assigned_manager_id = u.id
    """

    # Условия WHERE
    conditions = []
    params = []

    if show_pool:
        conditions.append("c.assigned_manager_id IS NULL")

    if not include_completed:
        conditions.append("c.status != 'completed'")

    if updated_since:
        conditions.append("c.updated_at IS NOT NULL AND c.updated_at > ?")
        params.append(updated_since)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # ORDER BY
    order_by = """
        ORDER BY 
            CASE WHEN c.response_timer > 0 THEN 0 ELSE 1 END,
            c.response_timer DESC,
            c.updated_at DESC
    """

    # LIMIT и OFFSET
    limit_clause = ""
    if limit:
        limit_clause = f" LIMIT {limit}"
        if offset:
            limit_clause += f" OFFSET {offset}"

    # Финальный запрос
    query = f"{base_query} {where_clause} {order_by}{limit_clause}"

    return query, tuple(params)
