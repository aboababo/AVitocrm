"""
Маршруты для работы с быстрыми ответами
"""

from database import get_connection
from flask import Blueprint, jsonify, request, session
from utils.decorators import handle_errors, require_auth
from utils.helpers import log_activity

quick_replies_bp = Blueprint("quick_replies", __name__)


@quick_replies_bp.route("/api/templates")
@require_auth
@handle_errors
def get_templates():
    """Получить список шаблонов сообщений"""
    with get_connection() as conn:
        templates = conn.execute(
        """
        SELECT id, name, content, category, created_by, is_active, created_at 
        FROM message_templates 
        WHERE is_active = 1 
        ORDER BY category, name
    """
    ).fetchall()
        return jsonify([dict(template) for template in templates])


@quick_replies_bp.route("/api/quick-replies")
@require_auth
@handle_errors
def get_quick_replies():
    """Получить список быстрых ответов"""
    with get_connection() as conn:
        replies = conn.execute(
        """
        SELECT id, shortcut, message, created_by, is_active, created_at 
        FROM quick_replies 
        WHERE is_active = 1 
        ORDER BY shortcut
    """
    ).fetchall()
        return jsonify([dict(reply) for reply in replies])


@quick_replies_bp.route("/api/quick-replies/all")
@require_auth
@handle_errors
def get_all_quick_replies():
    """Получение всех быстрых ответов (для управления)"""
    with get_connection() as conn:
        replies = conn.execute(
        """
        SELECT id, shortcut, message, created_by, is_active, created_at 
        FROM quick_replies 
        ORDER BY is_active DESC, shortcut
    """
    ).fetchall()
        return jsonify([dict(reply) for reply in replies])


@quick_replies_bp.route("/api/quick-replies", methods=["POST"])
@require_auth
@handle_errors
def create_quick_reply():
    """Создание быстрого ответа"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    shortcut = data.get("shortcut", "").strip()
    message = data.get("message", "").strip()

    if not shortcut or not message:
        return jsonify({"error": "Shortcut and message are required"}), 400

    # Убираем "/" если он есть в начале
    if shortcut.startswith("/"):
        shortcut = shortcut[1:]

    with get_connection() as conn:
        try:
            cursor = conn.execute(
            """
            INSERT INTO quick_replies (shortcut, message, created_by, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (shortcut, message, session["user_id"], True),
            )
            reply_id = cursor.lastrowid

            log_activity(
            session["user_id"],
            "create_quick_reply",
            f"Создан быстрый ответ: {shortcut}",
            "quick_reply",
            reply_id,
            )

            conn.commit()
            return jsonify({"success": True, "id": reply_id}), 201
        except Exception as e:
        if "UNIQUE constraint" in str(e):
            return (
                jsonify({"error": "Quick reply with this shortcut already exists"}),
                400,
            )
        return jsonify({"error": str(e)}), 400


@quick_replies_bp.route("/api/quick-replies/<int:reply_id>", methods=["PUT"])
@require_auth
@handle_errors
def update_quick_reply(reply_id):
    """Обновление быстрого ответа"""
    data = request.get_json()
    with get_connection() as conn:
        try:
            update_fields = []
            update_values = []

            if "shortcut" in data:
            shortcut = data["shortcut"].strip()
            if shortcut.startswith("/"):
                shortcut = shortcut[1:]
            update_fields.append("shortcut = ?")
            update_values.append(shortcut)

            if "message" in data:
            update_fields.append("message = ?")
            update_values.append(data["message"].strip())

            if "is_active" in data:
            update_fields.append("is_active = ?")
            update_values.append(data["is_active"])

            if update_fields:
                update_values.append(reply_id)
                query = f'UPDATE quick_replies SET {", ".join(update_fields)} WHERE id = ?'
                conn.execute(query, tuple(update_values))

                log_activity(
                    session["user_id"],
                    "update_quick_reply",
                    f"Обновлен быстрый ответ ID: {reply_id}",
                    "quick_reply",
                    reply_id,
                )

                conn.commit()

            return jsonify({"success": True}), 200
        except Exception as e:
        return jsonify({"error": str(e)}), 400


@quick_replies_bp.route("/api/quick-replies/<int:reply_id>", methods=["DELETE"])
@require_auth
@handle_errors
def delete_quick_reply(reply_id):
    """Удаление быстрого ответа (деактивация)"""
    with get_connection() as conn:
        try:
            conn.execute("UPDATE quick_replies SET is_active = 0 WHERE id = ?", (reply_id,))

            log_activity(
                session["user_id"],
                "delete_quick_reply",
                f"Удален быстрый ответ ID: {reply_id}",
                "quick_reply",
                reply_id,
            )

            conn.commit()
            return jsonify({"success": True}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
