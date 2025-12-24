"""
Маршруты для аналитики
"""

import json

from database import get_connection
from flask import Blueprint, jsonify, request, session
from utils.decorators import handle_errors, require_auth

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics")
@require_auth
@handle_errors
def get_analytics():
    """Получить аналитику"""
    user_id = session["user_id"]
    role = session.get("user_role")

    with get_connection() as conn:

        # Статистика ответов
        if role == "admin":
            response_stats = conn.execute(
                """
                SELECT
                    AVG(response_timer) as avg_response_time,
                    COUNT(*) as total_chats,
                    SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent_count
                FROM avito_chats
            """
            ).fetchone()
        else:
            response_stats = conn.execute(
                """
                SELECT
                    AVG(response_timer) as avg_response_time,
                    COUNT(*) as total_chats,
                    SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent_count
                FROM avito_chats
                WHERE assigned_manager_id = ?
            """,
                (user_id,),
            ).fetchone()

        # KPI менеджеров
        if role == "admin":
            kpi_stats = conn.execute(
                """
                SELECT u.id, u.username, u.kpi_score,
                       COUNT(DISTINCT c.id) as total_chats,
                       AVG(c.response_timer) as avg_response_time
                FROM users u
                LEFT JOIN avito_chats c ON u.id = c.assigned_manager_id
                WHERE u.role = 'manager'
                GROUP BY u.id
            """
            ).fetchall()
        else:
            kpi_stats = conn.execute(
                """
                SELECT u.id, u.username, u.kpi_score,
                       COUNT(DISTINCT c.id) as total_chats,
                       AVG(c.response_timer) as avg_response_time
                FROM users u
                LEFT JOIN avito_chats c ON u.id = c.assigned_manager_id
                WHERE u.id = ?
                GROUP BY u.id
            """,
                (user_id,),
            ).fetchall()

        # Конверсия в заказы
        conversion_stats = conn.execute(
            """
            SELECT
                COUNT(DISTINCT c.id) as total_chats,
                COUNT(DISTINCT o.id) as total_orders,
                ROUND(COUNT(DISTINCT o.id) * 100.0 / COUNT(DISTINCT c.id), 2) as conversion_rate
            FROM avito_chats c
            LEFT JOIN client_orders o ON c.id = o.chat_id
        """
        ).fetchone()

        return jsonify(
            {
                "response_stats": dict(response_stats),
                "kpi_stats": [dict(stat) for stat in kpi_stats],
                "conversion_stats": dict(conversion_stats),
            }
        )


@analytics_bp.route("/api/automation")
@require_auth
@handle_errors
def get_automation_rules():
    """Получить правила автоматизации"""
    with get_connection() as conn:
        rules = conn.execute(
            """
            SELECT id, name, trigger_type, trigger_condition, action_type, action_data, is_active, created_by, created_at
            FROM automation_rules
            WHERE is_active = 1
            ORDER BY created_at DESC
        """
        ).fetchall()
        return jsonify([dict(rule) for rule in rules])


@analytics_bp.route("/api/automation", methods=["POST"])
@require_auth
@handle_errors
def create_automation_rule():
    """Создать правило автоматизации"""
    if session.get("user_role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO automation_rules (name, trigger_type, trigger_condition, action_type, action_data, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("name"),
                    data.get("trigger_type"),
                    json.dumps(data.get("trigger_condition")),
                    data.get("action_type"),
                    json.dumps(data.get("action_data")),
                    session["user_id"],
                ),
            )
            conn.commit()
            return jsonify({"success": True, "id": cursor.lastrowid}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
