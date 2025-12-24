"""
Основные endpoints для работы с чатами
"""

import logging
import sqlite3
from functools import wraps

from avito_api import AvitoAPI
from database import get_db_connection
from flask import Blueprint, jsonify, request, session
from services.messenger_service import MessengerService

logger = logging.getLogger("app")

chats_bp = Blueprint("chats_api", __name__, url_prefix="/api/chats")


def handle_errors(f):
    """Декоратор для обработки ошибок"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as error:
            logger.error(f"Ошибка в {f.__name__}: {error}", exc_info=True)
            return jsonify({"error": str(error), "code": "INTERNAL_ERROR"}), 500

    return decorated_function


def require_auth(f):
    """Декоратор проверки аутентификации"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        return f(*args, **kwargs)

    return decorated_function


def _ensure_manager_can_access_chat(chat_row) -> bool:
    """
    Проверяет доступ к чату.
    Все аутентифицированные пользователи имеют доступ ко всем чатам.
    """
    return chat_row is not None


@chats_bp.route("/", methods=["GET"])
@require_auth
@handle_errors
def get_chats():
    """Получить список чатов"""
    logger.info(f"[CHATS_API] Запрос получен через chats_bp blueprint. Session: user_id={session.get('user_id')}")

    limit = max(1, min(request.args.get("limit", default=100, type=int), 500))
    offset = max(0, request.args.get("offset", default=0, type=int))

    # Пробуем получить соединение с обработкой ошибок диска
    max_retries = 3
    retry_count = 0
    conn = None

    while retry_count < max_retries:
        try:
            conn = get_db_connection()
            break
        except (sqlite3.OperationalError, RuntimeError) as conn_error:
            error_msg = str(conn_error).lower()
            if "disk i/o error" in error_msg or "i/o error" in error_msg:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"[GET_CHATS] Disk I/O error after {max_retries} retries: {conn_error}")
                    return (
                        jsonify(
                            {
                                "error": "Internal server error",
                                "message": "disk I/O error",
                                "code": "DISK_IO_ERROR",
                            }
                        ),
                        500,
                    )
                import time

                time.sleep(0.1 * retry_count)
                continue
            else:
                raise

    if conn is None:
        logger.error("[GET_CHATS] Failed to get database connection")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": "Failed to connect to database",
                    "code": "DB_CONNECTION_ERROR",
                }
            ),
            500,
        )

    try:
        # Параметры фильтрации
        shop_id = request.args.get("shop_id", type=int)
        pool_only = request.args.get("pool", "false").lower() == "true"
        manager_id = None  # Все видят все чаты

        # Создаём сервис
        service = MessengerService(conn, None)

        # Пробуем выполнить запрос с повторными попытками при disk I/O ошибках
        max_query_retries = 3
        query_retry_count = 0
        chats = None
        total = 0

        while query_retry_count < max_query_retries:
            try:
                chats, total = service.get_chats_list(
                    shop_id=shop_id,
                    manager_id=manager_id,
                    pool_only=pool_only,
                    limit=limit,
                    offset=offset,
                    with_total=True,
                )
                break
            except sqlite3.OperationalError as query_error:
                error_msg = str(query_error).lower()
                if (
                    "disk i/o error" in error_msg or "i/o error" in error_msg
                ) and query_retry_count < max_query_retries - 1:
                    query_retry_count += 1
                    logger.warning(
                        f"[GET_CHATS] Disk I/O error during query (attempt {query_retry_count}/{max_query_retries}), retrying..."
                    )
                    import time

                    time.sleep(0.1 * query_retry_count)
                    try:
                        conn = get_db_connection()
                        service = MessengerService(conn, None)
                    except Exception as reconnect_error:
                        logger.error(f"[GET_CHATS] Failed to reconnect: {reconnect_error}")
                        if query_retry_count >= max_query_retries:
                            raise
                        continue
                else:
                    raise

        if chats is None:
            raise RuntimeError("Failed to get chats after all retries")

        response = jsonify(
            {
                "items": chats,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            }
        )

        return response
    except Exception as e:
        logger.error(f"[GET_CHATS] Критическая ошибка: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": str(e),
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


@chats_bp.route("/<int:chat_id>/messages", methods=["GET"])
@require_auth
def get_messages(chat_id):
    """Получить сообщения чата"""
    limit = max(1, min(request.args.get("limit", default=50, type=int), 500))
    offset = max(0, request.args.get("offset", default=0, type=int))
    sync = request.args.get("sync", "false").lower() == "true"

    conn = get_db_connection()

    try:
        chat = conn.execute(
            """
            SELECT ac.*, s.client_id, s.client_secret, s.user_id
            FROM avito_chats ac
            JOIN avito_shops s ON ac.shop_id = s.id
            WHERE ac.id = ?
        """,
            (chat_id,),
        ).fetchone()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        chat = dict(chat)

        # Синхронизация сообщений, если запрошена
        should_sync = sync and chat.get("client_id") and chat.get("client_secret") and chat.get("user_id")

        if should_sync:
            try:
                api = AvitoAPI(client_id=chat["client_id"], client_secret=chat["client_secret"])
                service = MessengerService(conn, api)

                new_messages_count = service.sync_chat_messages(
                    chat_id=chat_id,
                    user_id=chat["user_id"],
                    avito_chat_id=chat.get("chat_id") or "",
                )
                logger.info(f"[API/MESSAGES] Синхронизация завершена: {new_messages_count} новых сообщений")
            except Exception as sync_error:
                logger.error(f"[API/MESSAGES] Ошибка синхронизации: {sync_error}", exc_info=True)
                service = MessengerService(conn, None)
        else:
            if sync:
                logger.warning("[API/MESSAGES] Синхронизация запрошена, но не выполнена")
            service = MessengerService(conn, None)

        # Получаем сообщения
        try:
            messages, total = service.get_chat_messages(chat_id, limit, offset)
        except Exception as msg_error:
            logger.error(f"[API/MESSAGES] Ошибка получения сообщений: {msg_error}", exc_info=True)
            return (
                jsonify(
                    {
                        "error": f"Error getting messages: {str(msg_error)}",
                        "code": "MESSAGES_ERROR",
                    }
                ),
                500,
            )

        logger.info(f"[API/MESSAGES] Возвращаем {len(messages)} сообщений из {total} всего")

        return jsonify(
            {
                "messages": messages,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            }
        )
    except Exception as e:
        logger.error(f"[API/MESSAGES] Критическая ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@chats_bp.route("/<int:chat_id>/send", methods=["POST"])
@require_auth
def send_message(chat_id):
    """Отправить сообщение в чат"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message is required"}), 400

    if len(message) > 5000:
        return jsonify({"error": "Message too long (max 5000 characters)"}), 400

    conn = get_db_connection()
    try:
        chat = conn.execute(
            """
            SELECT c.*, s.client_id, s.client_secret, s.user_id as shop_user_id
            FROM avito_chats c
            LEFT JOIN avito_shops s ON c.shop_id = s.id
            WHERE c.id = ?
        """,
            (chat_id,),
        ).fetchone()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        chat = dict(chat) if not isinstance(chat, dict) else chat

        from auth import get_user_by_id

        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Отправляем сообщение через Avito API, если есть ключи
        avito_message_sent = False
        avito_error = None

        if chat.get("client_id") and chat.get("client_secret") and chat.get("shop_user_id") and chat.get("chat_id"):
            try:
                api = AvitoAPI(
                    client_id=chat.get("client_id"),
                    client_secret=chat.get("client_secret"),
                )
                api.send_message(
                    user_id=str(chat.get("shop_user_id")),
                    chat_id=str(chat.get("chat_id")),
                    message=message,
                )
                avito_message_sent = True
                logger.info(f"[SEND MESSAGE] ✅ Успешно отправлено для чата {chat_id}")
            except Exception as e:
                avito_error = str(e)
                logger.error(f"[SEND MESSAGE] ❌ Ошибка отправки: {e}")

        # Сохраняем сообщение в БД
        manager_id = session["user_id"]
        cursor = conn.execute(
            """
            INSERT INTO avito_messages (chat_id, message_text, message_type, sender_name, manager_id)
            VALUES (?, ?, 'outgoing', ?, ?)
        """,
            (chat_id, message, user["username"], manager_id),
        )

        # Обновляем последнее сообщение в чате
        conn.execute(
            """
            UPDATE avito_chats 
            SET last_message = ?, updated_at = CURRENT_TIMESTAMP,
                assigned_manager_id = COALESCE(assigned_manager_id, ?),
                response_timer = 0
            WHERE id = ?
        """,
            (message, manager_id, chat_id),
        )

        from utils.helpers import log_activity

        log_activity(
            session["user_id"],
            "send_message",
            f"Отправлено сообщение в чат ID: {chat_id}",
            "chat",
            chat_id,
            {"message_length": len(message), "avito_sent": avito_message_sent},
        )

        conn.commit()

        # Синхронизируем сообщения после отправки
        if avito_message_sent:
            try:
                api_sync = AvitoAPI(client_id=chat["client_id"], client_secret=chat["client_secret"])
                service = MessengerService(conn, api_sync)
                service.sync_chat_messages(
                    chat_id=chat_id,
                    user_id=str(chat["shop_user_id"]),
                    avito_chat_id=str(chat["chat_id"]),
                )
            except Exception as sync_err:
                logger.warning(f"Не удалось синхронизировать сообщения: {sync_err}")

        response_data = {"success": True, "id": cursor.lastrowid}
        if avito_message_sent:
            response_data["avito_sent"] = True
        elif avito_error:
            response_data["warning"] = f"Сообщение сохранено в БД, но не отправлено в Avito: {avito_error}"

        return jsonify(response_data), 201
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@chats_bp.route("/<int:chat_id>/take", methods=["POST"])
@require_auth
def take_chat(chat_id):
    """Взять чат в работу"""
    conn = get_db_connection()
    try:
        chat = conn.execute("SELECT * FROM avito_chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if not _ensure_manager_can_access_chat(chat):
            return jsonify({"error": "Access denied"}), 403

        from auth import get_user_by_id

        user = get_user_by_id(session["user_id"])

        conn.execute(
            """
            UPDATE avito_chats 
            SET assigned_manager_id = ?, assigned_manager_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (session["user_id"], user["username"], chat_id),
        )

        from utils.helpers import log_activity

        log_activity(session["user_id"], "take_chat", f"Взят чат ID: {chat_id}", "chat", chat_id)

        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Ошибка взятия чата: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@chats_bp.route("/<int:chat_id>/return", methods=["POST"])
@require_auth
def return_chat(chat_id):
    """Вернуть чат в пул"""
    conn = get_db_connection()
    try:
        chat = conn.execute("SELECT * FROM avito_chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if not _ensure_manager_can_access_chat(chat):
            return jsonify({"error": "Access denied"}), 403

        conn.execute(
            """
            UPDATE avito_chats 
            SET assigned_manager_id = NULL, assigned_manager_name = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (chat_id,),
        )

        from utils.helpers import log_activity

        log_activity(
            session["user_id"],
            "return_chat",
            f"Возвращен чат ID: {chat_id}",
            "chat",
            chat_id,
        )

        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Ошибка возврата чата: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@chats_bp.route("/<int:chat_id>/block", methods=["POST"])
@require_auth
def block_chat(chat_id):
    """Заблокировать чат"""
    conn = get_db_connection()
    try:
        chat = conn.execute("SELECT * FROM avito_chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if not _ensure_manager_can_access_chat(chat):
            return jsonify({"error": "Access denied"}), 403

        conn.execute(
            """
            UPDATE avito_chats 
            SET status = 'blocked', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (chat_id,),
        )

        from utils.helpers import log_activity

        log_activity(
            session["user_id"],
            "block_chat",
            f"Заблокирован чат ID: {chat_id}",
            "chat",
            chat_id,
        )

        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Ошибка блокировки чата: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400
