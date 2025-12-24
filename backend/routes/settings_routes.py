"""
Маршруты для настроек системы и пользователей
"""

import json
import logging
import re

from auth import get_user_settings
from database import get_connection
from flask import Blueprint, jsonify, request, session
from utils.decorators import handle_errors, require_auth, require_role
from utils.helpers import check_name_columns, log_activity

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/api/settings")
@require_auth
@require_role("admin")
@handle_errors
def get_system_settings():
    """Получить настройки системы"""
    with get_connection() as conn:
        settings = conn.execute(
            """
            SELECT id, setting_key, setting_value, setting_type, description, updated_at 
            FROM system_settings
        """
        ).fetchall()

    settings_dict = {}
    for setting in settings:
        value = setting["setting_value"]
        if setting["setting_type"] == "number":
            value = float(value) if "." in value else int(value)
        elif setting["setting_type"] == "boolean":
            value = value.lower() == "true"
        elif setting["setting_type"] == "json":
            value = json.loads(value)
        settings_dict[setting["setting_key"]] = value

    return jsonify(settings_dict)


@settings_bp.route("/api/settings", methods=["PUT"])
@require_auth
@require_role("admin")
@handle_errors
def update_system_settings():
    """Обновить настройки системы"""
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    try:
        with get_connection() as conn:
            for key, value in data.items():
                setting_type = "string"
                if isinstance(value, bool):
                    setting_type = "boolean"
                    value = "true" if value else "false"
                elif isinstance(value, (int, float)):
                    setting_type = "number"
                    value = str(value)
                elif isinstance(value, dict):
                    setting_type = "json"
                    value = json.dumps(value)

                conn.execute(
                    """
                    UPDATE system_settings 
                    SET setting_value = ?, setting_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE setting_key = ?
                """,
                    (str(value), setting_type, key),
                )

            conn.commit()
            return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@settings_bp.route("/api/user/profile")
@require_auth
@handle_errors
def get_user_profile():
    """Получение профиля текущего пользователя"""
    try:
        with get_connection() as conn:
            has_name_cols = check_name_columns(conn)
            if has_name_cols:
                user = conn.execute(
                    """
                    SELECT id, username, email, first_name, last_name, role, is_active, created_at
                    FROM users
                    WHERE id = ?
                """,
                    (session["user_id"],),
                ).fetchone()
            else:
                user = conn.execute(
                    """
                    SELECT id, username, email, role, is_active, created_at
                    FROM users
                    WHERE id = ?
                """,
                    (session["user_id"],),
                ).fetchone()

            if not user:
                return jsonify({"error": "User not found"}), 404

            return jsonify(dict(user)), 200
    except Exception as e:
        logger.error(f"[GET USER PROFILE] Ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/user/profile", methods=["PUT"])
@require_auth
@handle_errors
def update_user_profile():
    """Обновление профиля текущего пользователя"""
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    first_name = (data.get("first_name") or "").strip() or None
    last_name = (data.get("last_name") or "").strip() or None

    if not username or not email:
        return jsonify({"error": "Username and email are required"}), 400

    email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    if not re.match(email_pattern, email):
        return jsonify({"error": "Invalid email format"}), 400

    try:
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id FROM users WHERE email = ? AND id != ?
            """,
                (email, session["user_id"]),
            ).fetchone()

            if existing:
                return jsonify({"error": "Email already in use"}), 400

            existing_username = conn.execute(
                """
                SELECT id FROM users WHERE username = ? AND id != ?
            """,
                (username, session["user_id"]),
            ).fetchone()

            if existing_username:
                return jsonify({"error": "Username already in use"}), 400

            has_name_cols = check_name_columns(conn)
            if has_name_cols:
                conn.execute(
                    """
                    UPDATE users 
                    SET username = ?, email = ?, first_name = ?, last_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (username, email, first_name, last_name, session["user_id"]),
                )
            else:
                conn.execute(
                    """
                    UPDATE users 
                    SET username = ?, email = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (username, email, session["user_id"]),
                )

            conn.commit()

            log_activity(
                session["user_id"],
                "update_profile",
                f"Пользователь обновил профиль: username={username}, email={email}",
                "user",
                session["user_id"],
            )

            return (
                jsonify({"success": True, "message": "Profile updated successfully"}),
                200,
            )
    except Exception as e:
        logger.error(f"[UPDATE USER PROFILE] Ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/user/settings")
@require_auth
@handle_errors
def get_user_settings_api():
    """Получение настроек пользователя"""
    settings = get_user_settings(session["user_id"])
    return jsonify(settings if settings else {})


@settings_bp.route("/api/user/settings", methods=["PUT"])
@require_auth
@handle_errors
def update_user_settings():
    """Обновление настроек пользователя"""
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    try:
        with get_connection() as conn:
            existing = conn.execute("SELECT id FROM user_settings WHERE user_id = ?", (session["user_id"],)).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE user_settings 
                    SET theme = ?, colors = ?, sound_alerts = ?, push_notifications = ?
                    WHERE user_id = ?
                """,
                    (
                        data.get("theme"),
                        json.dumps(data.get("colors", {})),
                        data.get("sound_alerts", True),
                        data.get("push_notifications", True),
                        session["user_id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_settings (user_id, theme, colors, sound_alerts, push_notifications)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        session["user_id"],
                        data.get("theme", "dark"),
                        json.dumps(data.get("colors", {})),
                        data.get("sound_alerts", True),
                        data.get("push_notifications", True),
                    ),
                )

            conn.commit()
            return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@settings_bp.route("/api/kpi/<int:user_id>")
@require_auth
@handle_errors
def get_manager_kpi(user_id):
    """Получить KPI менеджера"""
    if session.get("user_role") != "admin" and session["user_id"] != user_id:
        return jsonify({"error": "Access denied"}), 403

    with get_connection() as conn:
        kpi_settings = conn.execute(
            """
            SELECT id, parameter_name, weight, min_value, penalty_amount, bonus_amount, created_at 
            FROM kpi_settings
        """
        ).fetchall()

        kpi_history = conn.execute(
            """
            SELECT id, user_id, period_start, period_end, response_time_avg, conversion_rate, 
                   customer_satisfaction, messages_per_chat, total_score, bonus_amount, penalty_amount, created_at
            FROM kpi_history 
            WHERE user_id = ? 
            ORDER BY period_end DESC 
            LIMIT 12
        """,
            (user_id,),
        ).fetchall()

        user = conn.execute("SELECT kpi_score FROM users WHERE id = ?", (user_id,)).fetchone()

        return jsonify(
            {
                "settings": [dict(setting) for setting in kpi_settings],
                "history": [dict(record) for record in kpi_history],
                "current_score": user["kpi_score"] if user else 0,
            }
        )
