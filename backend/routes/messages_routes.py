"""
Маршруты для работы с сообщениями
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

from auth import get_user_by_id
from avito_api import AvitoAPI
from database import get_connection
from flask import Blueprint, jsonify, request, session
from services.messenger_service import MessengerService
from utils.decorators import handle_errors, require_auth
from utils.helpers import check_name_columns, log_activity

logger = logging.getLogger(__name__)

messages_bp = Blueprint("messages", __name__)


@messages_bp.route("/api/chats/<int:chat_id>/messages")
@require_auth
@handle_errors
def get_chat_messages(chat_id):
    """Получить сообщения чата с пагинацией"""
    # Параметры пагинации
    raw_limit = request.args.get("limit", default=50, type=int)
    raw_offset = request.args.get("offset", default=0, type=int)
    limit = max(1, min(raw_limit if raw_limit is not None else 50, 500))
    offset = max(0, raw_offset if raw_offset is not None else 0)
    before_id = request.args.get("before_id")
    sync = request.args.get("sync", "false").lower() == "true"

    # Получаем данные чата для синхронизации
    try:
        with get_connection() as conn:
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

            chat_dict = dict(chat)

            # Синхронизация сообщений, если запрошена и есть ключи
            should_sync = (
                sync and chat_dict.get("client_id") and chat_dict.get("client_secret") and chat_dict.get("user_id")
            )

            if should_sync:
                # Троттлинг: проверяем, когда была последняя синхронизация
                SYNC_COOLDOWN = 5
                last_sync_key = f"last_sync_{chat_id}"
                last_sync_time = getattr(get_chat_messages, last_sync_key, 0)
                current_time = time.time()
                time_since_last_sync = current_time - last_sync_time

                if time_since_last_sync < SYNC_COOLDOWN:
                    logger.info(f"[API/MESSAGES] ⏸️ Синхронизация пропущена: прошло только {time_since_last_sync:.1f} сек")
                    should_sync = False
                else:
                    setattr(get_chat_messages, last_sync_key, current_time)

            if should_sync:
                try:
                    avito_chat_id = chat_dict.get("chat_id")
                    if not avito_chat_id:
                        raise ValueError(f"avito_chat_id не найден для чата {chat_id}")

                    api = AvitoAPI(
                        client_id=chat_dict["client_id"],
                        client_secret=chat_dict["client_secret"],
                    )
                    service = MessengerService(conn, api)

                    new_messages_count = service.sync_chat_messages(
                        chat_id=chat_id,
                        user_id=chat_dict["user_id"],
                        avito_chat_id=avito_chat_id,
                    )
                    logger.info(f"[API/MESSAGES] Синхронизация завершена: {new_messages_count} новых сообщений")
                except Exception as sync_error:
                    logger.error(f"[API/MESSAGES] Ошибка синхронизации: {sync_error}", exc_info=True)
    except Exception as messages_error:
        logger.error(
            f"[API/MESSAGES] Ошибка получения данных чата: {messages_error}",
            exc_info=True,
        )
        return (
            jsonify({"error": "Internal server error", "message": str(messages_error)}),
            500,
        )

    # Базовый запрос сообщений из БД
    try:
        has_name_cols = check_name_columns(conn)
        if has_name_cols:
            query = """
                SELECT m.*, COALESCE(TRIM(u.first_name || ' ' || COALESCE(u.last_name, '')), u.username, 'Система') as manager_name
                FROM avito_messages m
                LEFT JOIN users u ON m.manager_id = u.id
                WHERE m.chat_id = ?
            """
        else:
            query = """
                SELECT m.*, COALESCE(u.username, 'Система') as manager_name
                FROM avito_messages m
                LEFT JOIN users u ON m.manager_id = u.id
                WHERE m.chat_id = ?
            """
        params = [chat_id]

        if before_id:
            try:
                before_id_int = int(before_id)
                query += " AND m.id < ?"
                params.append(before_id_int)
            except ValueError:
                pass

        query += " ORDER BY m.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        messages = conn.execute(query, tuple(params)).fetchall()

        # Получаем общее количество сообщений
        total_count = conn.execute(
            "SELECT COUNT(*) as count FROM avito_messages WHERE chat_id = ?", (chat_id,)
        ).fetchone()["count"]

        remaining_count = total_count
        if before_id:
            try:
                remaining_count = conn.execute(
                    "SELECT COUNT(*) as count FROM avito_messages WHERE chat_id = ? AND id < ?",
                    (chat_id, int(before_id)),
                ).fetchone()["count"]
            except ValueError:
                remaining_count = total_count

        log_activity(
            session["user_id"],
            "open_chat",
            f"Открыт чат ID: {chat_id}",
            "chat",
            chat_id,
        )

        messages_list = [dict(msg) for msg in reversed(messages)]

        return jsonify(
            {
                "messages": messages_list,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(messages_list)) < remaining_count,
            }
        )
    except Exception as query_error:
        logger.error(f"[API/MESSAGES] Ошибка запроса сообщений: {query_error}", exc_info=True)
        return (
            jsonify({"error": "Internal server error", "message": str(query_error)}),
            500,
        )


@messages_bp.route("/api/chats/<int:chat_id>/messages", methods=["POST"])
@require_auth
@handle_errors
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

    try:
        with get_connection() as conn:
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

        # Логируем событие
        conn.execute(
            """
            INSERT INTO analytics_logs (event_type, user_id, chat_id, metadata)
            VALUES ('message_sent', ?, ?, ?)
        """,
            (
                session["user_id"],
                chat_id,
                json.dumps(
                    {
                        "message_length": len(message),
                        "avito_sent": avito_message_sent,
                        "avito_error": avito_error,
                    }
                ),
            ),
        )

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


@messages_bp.route("/api/upload/image", methods=["POST"])
@require_auth
@handle_errors
def upload_image():
    """Загрузка изображения для отправки в чат"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.content_type or not file.content_type.startswith("image/"):
        return jsonify({"error": "File must be an image"}), 400

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    max_size = 24 * 1024 * 1024  # 24 МБ
    if file_size > max_size:
        return (
            jsonify({"error": f"File too large (max {max_size // 1024 // 1024} MB)"}),
            400,
        )

    try:
        import uuid

        temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)

        file_ext = os.path.splitext(file.filename)[1] or ".jpg"
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = os.path.join(temp_dir, temp_filename)

        file.save(temp_path)

        shop_user_id = request.form.get("user_id")
        if not shop_user_id:
            try:
                with get_connection() as conn:
                    last_chat = conn.execute(
                """
                SELECT s.user_id as shop_user_id, s.client_id, s.client_secret
                FROM avito_chats c
                LEFT JOIN avito_shops s ON c.shop_id = s.id
                WHERE c.id IN (
                    SELECT id FROM avito_chats 
                    ORDER BY updated_at DESC LIMIT 1
                )
                LIMIT 1
            """
            ).fetchone()

            if last_chat:
                last_chat = dict(last_chat)
                shop_user_id = last_chat.get("shop_user_id")
                client_id = last_chat.get("client_id")
                client_secret = last_chat.get("client_secret")
            else:
                return (
                    jsonify({"error": "No shop user_id found. Please select a chat first."}),
                    400,
                )
        else:
            with get_connection() as conn:
                shop = conn.execute(
                """
                SELECT client_id, client_secret, user_id
                FROM avito_shops
                WHERE user_id = ?
                LIMIT 1
            """,
                (shop_user_id,),
            ).fetchone()

            if not shop:
                return jsonify({"error": "Shop not found"}), 404

            shop = dict(shop)
            client_id = shop.get("client_id")
            client_secret = shop.get("client_secret")

        if not client_id or not client_secret:
            return (
                jsonify({"error": "Avito API credentials not configured for this shop"}),
                400,
            )

        api = AvitoAPI(client_id, client_secret)
        upload_results = api.upload_images(str(shop_user_id), [temp_path])

        try:
            os.remove(temp_path)
        except:
            pass

        if not upload_results or len(upload_results) == 0:
            return jsonify({"error": "Failed to upload image"}), 500

        upload_result = upload_results[0]
        image_id = upload_result.get("id") or upload_result.get("image_id") or upload_result.get("attachment_id")

        if not image_id:
            return (
                jsonify({"error": "Failed to get image_id from upload response"}),
                500,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "image_id": str(image_id),
                    "upload_result": upload_result,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Ошибка загрузки изображения: {e}", exc_info=True)
        try:
            if "temp_path" in locals():
                os.remove(temp_path)
        except:
            pass
        return jsonify({"error": str(e)}), 500


@messages_bp.route("/api/chats/<int:chat_id>/messages/image", methods=["POST"])
@require_auth
@handle_errors
def send_image_message(chat_id):
    """Отправка изображения в чат"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    image_id = data.get("image_id")
    if not image_id:
        return jsonify({"error": "image_id is required"}), 400

    try:
        with get_connection() as conn:
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

        if not chat.get("client_id") or not chat.get("client_secret"):
            return (
                jsonify({"error": "Avito API credentials not configured for this shop"}),
                400,
            )

        api = AvitoAPI(chat["client_id"], chat["client_secret"])

        result = api.send_image_message_direct(
            user_id=str(chat["shop_user_id"]),
            chat_id=str(chat["chat_id"]),
            image_id=str(image_id),
        )

        cursor = conn.execute(
            """
            INSERT INTO avito_messages 
            (chat_id, message_text, sender_type, created_at, avito_message_id, avito_sent)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                chat_id,
                "[Изображение]",
                "manager",
                datetime.now(timezone.utc),
                result.get("id") or result.get("message_id"),
                True,
            ),
        )

        conn.commit()

        log_activity(
            session["user_id"],
            "send_image",
            f"Отправлено изображение в чат ID: {chat_id}",
            "chat",
            chat_id,
        )

        return jsonify({"success": True, "id": cursor.lastrowid}), 201
    except Exception as e:
        logger.error(f"Ошибка отправки изображения: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400
