"""
Маршруты для работы с webhooks
"""

import logging
from datetime import datetime, timezone

from auth import get_user_by_id
from avito_api import AvitoAPI
from database import get_connection
from flask import Blueprint, jsonify, render_template, request, session
from utils.decorators import handle_errors, require_auth, require_role
from utils.helpers import log_activity

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.route("/admin/webhooks")
@require_auth
@require_role("super_admin")
@handle_errors
def webhooks_page():
    """Страница управления webhooks для супер-админа"""
    user = get_user_by_id(session["user_id"])
    return render_template("webhooks.html", user=user)


@webhooks_bp.route("/api/admin/webhooks", methods=["GET"])
@require_auth
@require_role("super_admin")
@handle_errors
def get_webhook_info():
    """Получение информации о текущем webhook v3"""
    try:
        with get_connection() as conn:
            shop = conn.execute(
            """
            SELECT client_id, client_secret, user_id
            FROM avito_shops
            WHERE client_id IS NOT NULL AND client_secret IS NOT NULL
            LIMIT 1
        """
        ).fetchone()
            if not shop:
                return (
                    jsonify({"webhook": None, "error": "No shops with API credentials found"}),
                    404,
                )

            shop = dict(shop) if not isinstance(shop, dict) else shop

            api = AvitoAPI(shop["client_id"], shop["client_secret"])
            webhook = api.get_webhook_v3()

            return jsonify({"webhook": webhook if webhook else None}), 200

    except Exception as e:
        logger.error(f"Ошибка получения информации о webhook: {e}", exc_info=True)
        return jsonify({"webhook": None, "error": str(e)}), 500


@webhooks_bp.route("/api/admin/webhooks", methods=["POST"])
@require_auth
@require_role("super_admin")
@handle_errors
def register_webhook():
    """Регистрация нового webhook v3"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    url = data.get("url", "").strip()
    types = data.get("types", ["message", "chat"])

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not url.startswith("https://"):
        return jsonify({"error": "URL must start with https://"}), 400

    if not isinstance(types, list) or len(types) == 0:
        return jsonify({"error": "Types must be a non-empty list"}), 400

    valid_types = ["message", "chat", "user"]
    for t in types:
        if t not in valid_types:
            return (
                jsonify({"error": f"Invalid type: {t}. Valid types: {valid_types}"}),
                400,
            )

    try:
        with get_connection() as conn:
            shop = conn.execute(
            """
            SELECT client_id, client_secret, user_id
            FROM avito_shops
            WHERE client_id IS NOT NULL AND client_secret IS NOT NULL
            LIMIT 1
        """
        ).fetchone()
            if not shop:
                return jsonify({"error": "No shops with API credentials found"}), 404

            shop = dict(shop) if not isinstance(shop, dict) else shop

            api = AvitoAPI(shop["client_id"], shop["client_secret"])
            result = api.register_webhook_v3(url=url, types=types)

            log_activity(
                session["user_id"],
                "register_webhook",
                f"Зарегистрирован webhook: {url}",
                "system",
            )

            return jsonify({"success": True, "webhook": result}), 201

    except Exception as e:
        logger.error(f"Ошибка регистрации webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@webhooks_bp.route("/api/admin/webhooks", methods=["PUT"])
@require_auth
@require_role("super_admin")
@handle_errors
def update_webhook():
    """Обновление webhook v3"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    url = data.get("url", "").strip()
    types = data.get("types", ["message", "chat"])

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not url.startswith("https://"):
        return jsonify({"error": "URL must start with https://"}), 400

    if not isinstance(types, list) or len(types) == 0:
        return jsonify({"error": "Types must be a non-empty list"}), 400

    valid_types = ["message", "chat", "user"]
    for t in types:
        if t not in valid_types:
            return (
                jsonify({"error": f"Invalid type: {t}. Valid types: {valid_types}"}),
                400,
            )

    try:
        with get_connection() as conn:
            shop = conn.execute(
            """
            SELECT client_id, client_secret, user_id
            FROM avito_shops
            WHERE client_id IS NOT NULL AND client_secret IS NOT NULL
            LIMIT 1
        """
        ).fetchone()
            if not shop:
                return jsonify({"error": "No shops with API credentials found"}), 404

            shop = dict(shop) if not isinstance(shop, dict) else shop

            api = AvitoAPI(shop["client_id"], shop["client_secret"])
            result = api.update_webhook_v3(url=url, types=types)

            log_activity(session["user_id"], "update_webhook", f"Обновлен webhook: {url}", "system")

            return jsonify({"success": True, "webhook": result}), 200

    except Exception as e:
        logger.error(f"Ошибка обновления webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@webhooks_bp.route("/api/admin/webhooks", methods=["DELETE"])
@require_auth
@require_role("super_admin")
@handle_errors
def delete_webhook():
    """Удаление webhook v3"""
    try:
        with get_connection() as conn:
            shop = conn.execute(
            """
            SELECT client_id, client_secret, user_id
            FROM avito_shops
            WHERE client_id IS NOT NULL AND client_secret IS NOT NULL
            LIMIT 1
        """
        ).fetchone()
            if not shop:
                return jsonify({"error": "No shops with API credentials found"}), 404

            shop = dict(shop) if not isinstance(shop, dict) else shop

            api = AvitoAPI(shop["client_id"], shop["client_secret"])
            success = api.delete_webhook_v3()

            if success:
                log_activity(session["user_id"], "delete_webhook", "Удален webhook", "system")

                return (
                    jsonify({"success": True, "message": "Webhook deleted successfully"}),
                    200,
                )
            else:
                return jsonify({"error": "Failed to delete webhook"}), 500

    except Exception as e:
        logger.error(f"Ошибка удаления webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@webhooks_bp.route("/webhook/avito", methods=["GET"])
def webhook_test():
    """Тестовый endpoint для проверки доступности webhook"""
    return (
        jsonify(
            {
                "status": "ok",
                "message": "Webhook endpoint is accessible",
                "url": "https://osagaming.store/webhook/avito",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        200,
    )


@webhooks_bp.route("/webhook/avito", methods=["POST"])
def avito_webhook():
    """
    Обработчик webhook от Авито

    Получает уведомления о новых сообщениях, изменениях в чатах и т.д.
    Автоматически синхронизирует чаты при получении уведомлений.
    """
    try:
        # Получаем данные webhook
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        logger.info(f"[WEBHOOK] Получен webhook от Авито: {data}")

        # Обрабатываем структуру webhook v3
        payload = data.get("payload", {})
        if not payload:
            event_type = data.get("type")
            event_data = data.get("data", {})
        else:
            event_type = payload.get("type")
            event_data = payload.get("value", {})

            if event_type in ["new_message", "message"]:
                event_type = "message"
            elif event_type in ["chat_update", "chat"]:
                event_type = "chat"

        logger.info(f"[WEBHOOK] Тип события: {event_type}, данные: {event_data}")

        with get_connection() as conn:

            if event_type in ["message", "new_message"]:
            # Новое сообщение - синхронизируем чат
            avito_chat_id = event_data.get("chat_id")
            user_id = event_data.get("user_id")

            if avito_chat_id and user_id:
                # Находим магазин по user_id
                shop = conn.execute(
                    """
                    SELECT id, client_id, client_secret, user_id 
                    FROM avito_shops 
                    WHERE user_id = ?
                """,
                    (user_id,),
                ).fetchone()

                if shop:
                    shop = dict(shop)
                    # Находим чат в БД
                    chat = conn.execute(
                        """
                        SELECT id FROM avito_chats 
                        WHERE chat_id = ? AND shop_id = ?
                    """,
                        (avito_chat_id, shop["id"]),
                    ).fetchone()

                    if chat:
                        # Синхронизируем сообщения
                        try:
                            from services.messenger_service import MessengerService

                            api = AvitoAPI(shop["client_id"], shop["client_secret"])
                            service = MessengerService(conn, api)
                            service.sync_chat_messages(
                                chat_id=chat["id"],
                                user_id=str(user_id),
                                avito_chat_id=str(avito_chat_id),
                            )
                            logger.info(f"[WEBHOOK] Синхронизирован чат {chat['id']} после webhook")
                        except Exception as sync_err:
                            logger.error(
                                f"[WEBHOOK] Ошибка синхронизации: {sync_err}",
                                exc_info=True,
                            )

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"[WEBHOOK] Ошибка обработки webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
