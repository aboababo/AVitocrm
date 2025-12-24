"""
Маршруты для работы с доставками
"""

from database import get_connection
from flask import Blueprint, jsonify, request, session
from utils.decorators import handle_errors, require_auth
from utils.helpers import check_name_columns, log_activity

deliveries_bp = Blueprint("deliveries", __name__)


@deliveries_bp.route("/api/deliveries")
@require_auth
@handle_errors
def get_deliveries():
    """Получить список доставок"""
    with get_connection() as conn:
        has_name_cols = check_name_columns(conn)
        if session.get("user_role") == "admin":
            if has_name_cols:
                deliveries = conn.execute(
                    """
                    SELECT d.*, c.client_name, c.client_phone, c.id as chat_id, c.response_timer, 
                           COALESCE(
                               NULLIF(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), ''),
                               u.username,
                               'Система'
                           ) as manager_name
                    FROM deliveries d
                    LEFT JOIN avito_chats c ON d.chat_id = c.id
                    LEFT JOIN users u ON d.manager_id = u.id
                    ORDER BY d.updated_at DESC
                    LIMIT 1000
                """
                ).fetchall()
            else:
                deliveries = conn.execute(
                    """
                    SELECT d.*, c.client_name, c.client_phone, c.id as chat_id, c.response_timer, 
                           COALESCE(u.username, 'Система') as manager_name
                    FROM deliveries d
                    LEFT JOIN avito_chats c ON d.chat_id = c.id
                    LEFT JOIN users u ON d.manager_id = u.id
                    ORDER BY d.updated_at DESC
                    LIMIT 1000
                """
                ).fetchall()
        else:
            deliveries = conn.execute(
                """
                SELECT d.*, c.client_name, c.client_phone, c.id as chat_id, c.response_timer
                FROM deliveries d
                LEFT JOIN avito_chats c ON d.chat_id = c.id
                WHERE d.manager_id = ?
                ORDER BY d.updated_at DESC
                LIMIT 1000
            """,
                (session["user_id"],),
            ).fetchall()

        result = [dict(delivery) for delivery in deliveries]
        return jsonify(result)


@deliveries_bp.route("/api/deliveries", methods=["POST"])
@require_auth
@handle_errors
def create_delivery():
    """Создать новую доставку"""
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    with get_connection() as conn:
        chat_id = data.get("chat_id")
        cursor = conn.execute(
            """
            INSERT INTO deliveries (chat_id, manager_id, delivery_status, address, tracking_number, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                chat_id if chat_id else None,
                session["user_id"],
                data.get("status", "processing"),
                data.get("address"),
                data.get("tracking_number"),
                data.get("notes"),
            ),
        )

        # Обновляем приоритет чата на delivery, если chat_id указан
        if chat_id:
            conn.execute('UPDATE avito_chats SET priority = "delivery" WHERE id = ?', (chat_id,))

        log_activity(
            session["user_id"],
            "create_delivery",
            f"Создана доставка ID: {cursor.lastrowid}",
            "delivery",
            cursor.lastrowid,
        )

        conn.commit()
        return jsonify({"success": True, "id": cursor.lastrowid}), 201


@deliveries_bp.route("/api/deliveries/<int:delivery_id>", methods=["PUT"])
@require_auth
@handle_errors
def update_delivery(delivery_id):
    """Обновить доставку"""
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    with get_connection() as conn:
        # Проверяем существование доставки
        delivery = conn.execute("SELECT id, manager_id FROM deliveries WHERE id = ?", (delivery_id,)).fetchone()
        if not delivery:
            return jsonify({"error": "Delivery not found"}), 404

        # Проверяем права доступа (только создатель или админ)
        if delivery["manager_id"] != session["user_id"] and session.get("user_role") != "admin":
            return jsonify({"error": "Access denied"}), 403

        # Обновляем доставку
        conn.execute(
            """
            UPDATE deliveries
            SET delivery_status = ?, address = ?, tracking_number = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (
                data.get("status", delivery.get("delivery_status")),
                data.get("address"),
                data.get("tracking_number"),
                data.get("notes"),
                delivery_id,
            ),
        )
        conn.commit()

        log_activity(
            session["user_id"],
            "update_delivery",
            f"Обновлена доставка ID: {delivery_id}",
            "delivery",
            delivery_id,
        )

        return jsonify({"success": True}), 200


@deliveries_bp.route("/api/deliveries/batch", methods=["PUT"])
@require_auth
@handle_errors
def batch_update_deliveries():
    """Массовое обновление доставок"""
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    deliveries = data.get("deliveries", [])
    if not isinstance(deliveries, list) or len(deliveries) == 0:
        return jsonify({"error": "deliveries array is required"}), 400

    updated_count = 0
    errors = []

    with get_connection() as conn:
        for delivery_data in deliveries:
            delivery_id = delivery_data.get("id")
            if not delivery_id:
                errors.append({"delivery": delivery_data, "error": "ID is required"})
                continue

            # Проверяем существование и права доступа
            delivery = conn.execute("SELECT id, manager_id FROM deliveries WHERE id = ?", (delivery_id,)).fetchone()
            if not delivery:
                errors.append({"id": delivery_id, "error": "Delivery not found"})
                continue

            if delivery["manager_id"] != session["user_id"] and session.get("user_role") != "admin":
                errors.append({"id": delivery_id, "error": "Access denied"})
                continue

            # Обновляем доставку
            try:
                conn.execute(
                    """
                    UPDATE deliveries
                    SET delivery_status = ?, address = ?, tracking_number = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (
                        delivery_data.get("status"),
                        delivery_data.get("address"),
                        delivery_data.get("tracking_number"),
                        delivery_data.get("notes"),
                        delivery_id,
                    ),
                )
                updated_count += 1
            except Exception as e:
                errors.append({"id": delivery_id, "error": str(e)})

        conn.commit()

        log_activity(
            session["user_id"],
            "batch_update_deliveries",
            f"Массовое обновление доставок: {updated_count} обновлено",
            "delivery",
            None,
        )

        return (
            jsonify({"success": True, "updated": updated_count, "errors": errors}),
            200,
        )
