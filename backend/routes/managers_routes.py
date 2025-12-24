"""
Маршруты для управления менеджерами
"""

import logging

from auth import generate_temp_password, hash_password
from database import get_connection
from flask import Blueprint, jsonify, request, session
from utils.decorators import handle_errors, require_auth, require_role
from utils.helpers import check_name_columns, log_activity
from utils.validators import validate_email

logger = logging.getLogger(__name__)

managers_bp = Blueprint("managers", __name__)


@managers_bp.route("/api/managers", methods=["POST"])
@require_auth
@require_role("admin")
@handle_errors
def create_manager():
    """Создание нового менеджера админом с генерацией одноразового пароля"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    salary = float(data.get("salary", 0) or 0)
    role = data.get("role", "manager")

    if role not in ["manager", "admin"]:
        role = "manager"
    if role == "admin" and user_role != "super_admin":
        return jsonify({"error": "Only super admin can create admin accounts"}), 403

    if not username or not email:
        return jsonify({"error": "Username and email are required"}), 400

    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    temp_password = generate_temp_password()
    hashed_password = hash_password(temp_password)

    first_name = (data.get("first_name") or "").strip() or None
    last_name = (data.get("last_name") or "").strip() or None

    try:
        with get_connection() as conn:
            existing_user = conn.execute(
                "SELECT id, username, email, is_active FROM users WHERE email = ?", (email,)
            ).fetchone()

            if existing_user:
                existing_dict = dict(existing_user)
                status_text = "активен" if existing_dict.get("is_active") else "неактивен"
                return (
                    jsonify(
                        {
                            "error": f'Пользователь с email {email} уже существует (ID: {existing_dict.get("id")}, статус: {status_text})'
                        }
                    ),
                    400,
                )

            has_name_cols = check_name_columns(conn)
            if has_name_cols:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, email, password, temp_password, role, salary, is_active, created_by, password_changed, first_name, last_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        username,
                        email,
                        hashed_password,
                        temp_password,
                        role,
                        salary,
                        True,
                        session["user_id"],
                        False,
                        first_name,
                        last_name,
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, email, password, temp_password, role, salary, is_active, created_by, password_changed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        username,
                        email,
                        hashed_password,
                        temp_password,
                        role,
                        salary,
                        True,
                        session["user_id"],
                        False,
                    ),
                )

            manager_id = cursor.lastrowid

            log_activity(
                session["user_id"],
                "create_user",
                f"Создан пользователь: {username} ({email}) с ролью {role}",
                "user",
                manager_id,
            )

            conn.commit()

            logger.info(
                f"[CREATE USER] Пользователь успешно создан: ID={manager_id}, username={username}, email={email}"
            )
            return (
                jsonify(
                    {
                        "success": True,
                        "id": manager_id,
                        "temp_password": temp_password,
                        "message": f"Пользователь создан. Одноразовый пароль: {temp_password}",
                    }
                ),
                201,
            )
    except Exception as e:
        logger.error(
            f"[CREATE USER] Ошибка при создании пользователя в БД: {e}",
            exc_info=True,
        )
        if "UNIQUE constraint" in str(e):
            return jsonify({"error": "User with this email already exists"}), 400
        return jsonify({"error": str(e)}), 400


@managers_bp.route("/api/managers/<int:manager_id>", methods=["PUT"])
@require_auth
@require_role("admin")
@handle_errors
def update_manager(manager_id):
    """Обновление данных менеджера или админа"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return (
            jsonify({"error": "Access denied. Only admin and super_admin can edit users"}),
            403,
        )

    data = request.get_json() or {}
    try:
        with get_connection() as conn:
            target_user = conn.execute("SELECT id, role FROM users WHERE id = ?", (manager_id,)).fetchone()
            if not target_user:
                return jsonify({"error": "User not found"}), 404

            target_user_dict = dict(target_user)
            target_role = target_user_dict.get("role")

            if target_role == "admin" and user_role != "super_admin":
                return jsonify({"error": "Only super_admin can edit admin accounts"}), 403

            update_fields = []
            update_values = []

            if "username" in data:
                update_fields.append("username = ?")
                update_values.append(data["username"])

            if "email" in data:
                if not validate_email(data["email"]):
                    return jsonify({"error": "Invalid email format"}), 400

                existing_user = conn.execute(
                    "SELECT id, username, email FROM users WHERE email = ? AND id != ?",
                    (data["email"], manager_id),
                ).fetchone()

                if existing_user:
                    existing_dict = dict(existing_user)
                    return (
                        jsonify(
                            {
                                "error": f'Email {data["email"]} уже используется другим пользователем (ID: {existing_dict.get("id")}, имя: {existing_dict.get("username")})'
                            }
                        ),
                        400,
                    )

                update_fields.append("email = ?")
                update_values.append(data["email"])

            if "first_name" in data:
                first_name = (data["first_name"] or "").strip() or None
                update_fields.append("first_name = ?")
                update_values.append(first_name)

            if "last_name" in data:
                last_name = (data["last_name"] or "").strip() or None
                update_fields.append("last_name = ?")
                update_values.append(last_name)

            if "password" in data and data["password"]:
                if len(data["password"]) < 6:
                    return jsonify({"error": "Password must be at least 6 characters"}), 400
                hashed_password = hash_password(data["password"])
                update_fields.append("password = ?")
                update_values.append(hashed_password)

            if "salary" in data:
                update_fields.append("salary = ?")
                update_values.append(data["salary"])

            if "is_active" in data:
                update_fields.append("is_active = ?")
                update_values.append(data["is_active"])

            if "role" in data:
                if user_role == "super_admin":
                    new_role = data["role"]
                    if new_role in ["manager", "admin"]:
                        update_fields.append("role = ?")
                        update_values.append(new_role)

            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(manager_id)
                query = f'UPDATE users SET {", ".join(update_fields)} WHERE id = ?'
                conn.execute(query, tuple(update_values))

                log_activity(
                    session["user_id"],
                    "update_manager",
                    f"Обновлен пользователь ID: {manager_id} (роль: {target_role})",
                    "user",
                    manager_id,
                )

                conn.commit()

            return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"[UPDATE MANAGER] Ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@managers_bp.route("/api/managers/<int:manager_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
@handle_errors
def delete_manager(manager_id):
    """Удаление пользователя (деактивация)"""
    user_role = session.get("user_role")
    current_user_id = session.get("user_id")

    if user_role not in ["admin", "super_admin"]:
        return jsonify({"error": "Access denied"}), 403

    if manager_id == current_user_id:
        return jsonify({"error": "Нельзя удалить свой собственный аккаунт"}), 400

    try:
        with get_connection() as conn:
            user_to_delete = conn.execute(
                """
                SELECT id, username, email, role, is_active
                FROM users
                WHERE id = ?
            """,
                (manager_id,),
            ).fetchone()

            if not user_to_delete:
                return jsonify({"error": "Пользователь не найден"}), 404

            user_dict = dict(user_to_delete)
            target_role = user_dict.get("role")
            target_username = user_dict.get("username", "Unknown")

            if user_role == "admin" and target_role != "manager":
                return (
                    jsonify({"error": "Только супер-админ может удалять администраторов"}),
                    403,
                )

            conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (manager_id,))

            role_text = "администратор" if target_role == "admin" else "менеджер"
            log_activity(
                current_user_id,
                "delete_user",
                f"Деактивирован {role_text}: {target_username} (ID: {manager_id})",
                "user",
                manager_id,
            )

            conn.commit()
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Пользователь {target_username} успешно деактивирован",
                    }
                ),
                200,
            )
    except Exception as e:
        logger.error(
            f"[DELETE USER] Ошибка удаления пользователя {manager_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": str(e)}), 400


@managers_bp.route("/api/managers/<int:manager_id>/reset-password", methods=["POST"])
@require_auth
@require_role("admin")
@handle_errors
def reset_user_password(manager_id):
    """Сброс пароля пользователя с генерацией нового одноразового пароля"""
    user_role = session.get("user_role")
    current_user_id = session.get("user_id")

    if user_role not in ["admin", "super_admin"]:
        return jsonify({"error": "Access denied"}), 403

    if manager_id == current_user_id:
        return (
            jsonify({"error": "Нельзя сбросить пароль своему собственному аккаунту"}),
            400,
        )

    try:
        with get_connection() as conn:
            user_to_reset = conn.execute(
                """
                SELECT id, username, email, role, is_active
                FROM users
                WHERE id = ?
            """,
                (manager_id,),
            ).fetchone()

            if not user_to_reset:
                return jsonify({"error": "Пользователь не найден"}), 404

            user_dict = dict(user_to_reset)
            target_role = user_dict.get("role")
            target_username = user_dict.get("username", "Unknown")

            if user_role == "admin" and target_role != "manager":
                return (
                    jsonify({"error": "Только супер-админ может сбрасывать пароли администраторам"}),
                    403,
                )

            if not user_dict.get("is_active"):
                return (
                    jsonify({"error": "Нельзя сбросить пароль неактивному пользователю"}),
                    400,
                )

            temp_password = generate_temp_password()
            hashed_password = hash_password(temp_password)

            conn.execute(
                """
                UPDATE users
                SET password = ?, temp_password = ?, password_changed = 0
                WHERE id = ?
            """,
                (hashed_password, temp_password, manager_id),
            )

            role_text = "администратору" if target_role == "admin" else "менеджеру"
            log_activity(
                current_user_id,
                "reset_password",
                f"Сброшен пароль {role_text}: {target_username} (ID: {manager_id})",
                "user",
                manager_id,
            )

            conn.commit()

            logger.info(f"[RESET PASSWORD] Пароль сброшен для пользователя ID={manager_id}, username={target_username}")
            return (
                jsonify(
                    {
                        "success": True,
                        "temp_password": temp_password,
                        "message": f"Пароль успешно сброшен для пользователя {target_username}. Новый одноразовый пароль: {temp_password}",
                    }
                ),
                200,
            )
    except Exception as e:
        logger.error(
            f"[RESET PASSWORD] Ошибка сброса пароля пользователя {manager_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": str(e)}), 400


@managers_bp.route("/api/work-schedules/<int:user_id>")
@require_auth
@handle_errors
def get_work_schedule(user_id):
    """Получение графика работы пользователя"""
    if session.get("user_role") != "admin" and session["user_id"] != user_id:
        return jsonify({"error": "Access denied"}), 403

    with get_connection() as conn:
        schedules = conn.execute(
        """
        SELECT id, user_id, day_of_week, start_time, end_time, is_working_day, created_at, updated_at 
        FROM work_schedules 
        WHERE user_id = ?
        ORDER BY day_of_week
    """,
        (user_id,),
    ).fetchall()

    return jsonify([dict(schedule) for schedule in schedules])


@managers_bp.route("/api/work-schedules")
@require_auth
@require_role("admin")
@handle_errors
def get_all_work_schedules():
    """Получение всех графиков работы (только админ)"""
    with get_connection() as conn:
        schedules = conn.execute(
        """
        SELECT ws.*, u.username, u.email, u.role
        FROM work_schedules ws
        JOIN users u ON ws.user_id = u.id
        ORDER BY u.username, ws.day_of_week
    """
    ).fetchall()

    return jsonify([dict(schedule) for schedule in schedules])


@managers_bp.route("/api/work-schedules", methods=["POST", "PUT"])
@require_auth
@require_role("admin")
@handle_errors
def save_work_schedule():
    """Создание или обновление графика работы (только админ)"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_id = data.get("user_id")
    day_of_week = data.get("day_of_week")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    is_working_day = data.get("is_working_day", True)

    if user_id is None or day_of_week is None:
        return jsonify({"error": "user_id and day_of_week are required"}), 400

    if is_working_day and (not start_time or not end_time):
        return (
            jsonify({"error": "start_time and end_time are required for working days"}),
            400,
        )

    with get_connection() as conn:
        try:
            existing = conn.execute(
            """
            SELECT id FROM work_schedules 
            WHERE user_id = ? AND day_of_week = ?
        """,
            (user_id, day_of_week),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE work_schedules 
                SET start_time = ?, end_time = ?, is_working_day = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (
                    start_time if is_working_day else None,
                    end_time if is_working_day else None,
                    is_working_day,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO work_schedules (user_id, day_of_week, start_time, end_time, is_working_day)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    day_of_week,
                    start_time if is_working_day else None,
                    end_time if is_working_day else None,
                    is_working_day,
                ),
            )

        log_activity(
            session["user_id"],
            "update_work_schedule",
            f"Обновлен график работы для пользователя ID: {user_id}, день: {day_of_week}",
            "work_schedule",
            user_id,
        )

            conn.commit()
            return jsonify({"success": True}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
