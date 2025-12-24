"""
OSAGAMING CRM - Оптимизатор запросов к БД
==========================================

Утилиты для оптимизации запросов к базе данных:
- Объединение множественных COUNT запросов
- Batch операции
- Оптимизированные JOIN запросы
"""

from typing import Any, Dict, List, Optional

from database import get_connection


def get_stats_batch(conn=None) -> Dict[str, Any]:
    """
    Получить все статистики одним запросом вместо множественных COUNT

    Args:
        conn: Соединение с БД (если None, создается новое)

    Returns:
        dict: Словарь со всеми статистиками
    """
    if conn is None:
        with get_connection() as conn:
            # Один запрос вместо множественных COUNT
            stats = conn.execute(
                """
        SELECT 
            (SELECT COUNT(*) FROM avito_chats) as total_chats,
            (SELECT COUNT(*) FROM avito_chats WHERE status = 'active') as active_chats,
            (SELECT COUNT(*) FROM avito_chats WHERE priority = 'urgent') as urgent_chats,
            (SELECT COUNT(*) FROM avito_chats WHERE unread_count > 0) as unread_chats,
            (SELECT COUNT(*) FROM avito_chats WHERE assigned_manager_id IS NULL AND status != 'completed') as pool_chats,
            (SELECT AVG(response_timer) FROM avito_chats WHERE response_timer IS NOT NULL) as avg_response_time,
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM users WHERE role = 'manager') as total_managers,
            (SELECT COUNT(*) FROM avito_shops) as total_shops,
            (SELECT COUNT(*) FROM avito_shops 
             WHERE client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL) as shops_with_keys
    """
            ).fetchone()

            return {
                "total_chats": stats["total_chats"] or 0,
                "active_chats": stats["active_chats"] or 0,
                "urgent_chats": stats["urgent_chats"] or 0,
                "unread_chats": stats["unread_chats"] or 0,
                "pool_chats": stats["pool_chats"] or 0,
                "avg_response_time": round(stats["avg_response_time"] or 0, 2),
                "total_users": stats["total_users"] or 0,
                "total_managers": stats["total_managers"] or 0,
                "total_shops": stats["total_shops"] or 0,
                "shops_with_keys": stats["shops_with_keys"] or 0,
            }


def get_chats_optimized(
    conn,
    show_pool: bool = False,
    include_completed: bool = True,
    updated_since: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    has_name_columns: bool = True,
) -> List[Dict[str, Any]]:
    """
    Оптимизированная функция получения чатов с одним запросом

    Args:
        conn: Соединение с БД
        show_pool: Показывать только чаты без менеджера
        include_completed: Включать завершенные чаты
        updated_since: Фильтр по времени обновления
        limit: Лимит результатов
        offset: Смещение для пагинации
        has_name_columns: Наличие колонок first_name/last_name

    Returns:
        list: Список чатов
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

    result = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in result]


def get_user_batch(user_ids: List[int], conn=None) -> Dict[int, Dict[str, Any]]:
    """
    Получить несколько пользователей одним запросом

    Args:
        user_ids: Список ID пользователей
        conn: Соединение с БД

    Returns:
        dict: Словарь {user_id: user_data}
    """
    if not user_ids:
        return {}

    if conn is None:
        with get_connection() as conn:
            placeholders = ",".join("?" * len(user_ids))
            users = conn.execute(
                f"SELECT id, username, email, role, first_name, last_name FROM users WHERE id IN ({placeholders})",
                tuple(user_ids),
            ).fetchall()

            return {user["id"]: dict(user) for user in users}

    placeholders = ",".join("?" * len(user_ids))
    users = conn.execute(
        f"SELECT id, username, email, role, first_name, last_name FROM users WHERE id IN ({placeholders})",
        tuple(user_ids),
    ).fetchall()

    return {user["id"]: dict(user) for user in users}


def get_shop_batch(shop_ids: List[int], conn=None) -> Dict[int, Dict[str, Any]]:
    """
    Получить несколько магазинов одним запросом

    Args:
        shop_ids: Список ID магазинов
        conn: Соединение с БД

    Returns:
        dict: Словарь {shop_id: shop_data}
    """
    if not shop_ids:
        return {}

    if conn is None:
        with get_connection() as conn:
            placeholders = ",".join("?" * len(shop_ids))
            shops = conn.execute(
                f"""
                SELECT 
                    id, name, shop_url, is_active, client_id, client_secret, user_id, webhook_registered,
                    CASE 
                        WHEN client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL 
                        THEN 'ok' ELSE 'missing' 
                    END AS avito_status
                FROM avito_shops 
                WHERE id IN ({placeholders})
                """,
                tuple(shop_ids),
            ).fetchall()

            return {shop["id"]: dict(shop) for shop in shops}

    placeholders = ",".join("?" * len(shop_ids))
    shops = conn.execute(
        f"""
        SELECT 
            id, name, shop_url, is_active, client_id, client_secret, user_id, webhook_registered,
            CASE 
                WHEN client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL 
                THEN 'ok' ELSE 'missing' 
            END AS avito_status
        FROM avito_shops 
        WHERE id IN ({placeholders})
        """,
        tuple(shop_ids),
    ).fetchall()

    return {shop["id"]: dict(shop) for shop in shops}
