"""
Маршруты для работы с магазинами
"""

import logging
import os

from avito_api import AvitoAPI
from database import get_connection
from flask import Blueprint, jsonify, request, session
from utils.decorators import handle_errors, require_auth, require_role
from utils.helpers import log_activity

logger = logging.getLogger(__name__)

shops_bp = Blueprint("shops", __name__)


@shops_bp.route("/api/shops")
@require_auth
@handle_errors
def get_shops():
    """Получить список магазинов"""
    user_role = session.get("user_role")

    with get_connection() as conn:

        if user_role in ["admin", "super_admin"]:
        # Админ и супер-админ видят все магазины
        shops = conn.execute(
            """
            SELECT 
                *, 
                CASE 
                    WHEN client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL 
                    THEN 'ok' ELSE 'missing' 
                END AS avito_status
            FROM avito_shops 
            ORDER BY created_at DESC
        """
        ).fetchall()
        logger.info(f"[GET SHOPS] Загружено магазинов для {user_role}: {len(shops)}")
        else:
        # Менеджер видит только назначенные магазины
        shops = conn.execute(
            """
            SELECT 
                s.*,
                CASE 
                    WHEN s.client_id IS NOT NULL AND s.client_secret IS NOT NULL AND s.user_id IS NOT NULL 
                    THEN 'ok' ELSE 'missing' 
                END AS avito_status
            FROM avito_shops s
            JOIN manager_assignments ma ON s.id = ma.shop_id
            WHERE ma.manager_id = ? AND s.is_active = 1
            ORDER BY s.created_at DESC
        """,
            (session["user_id"],),
        ).fetchall()

        shops_list = []
        for shop in shops:
        d = dict(shop)
        # Скрываем ключи только для менеджеров, админы и super_admin видят все
        if user_role not in ["admin", "super_admin"]:
            d.pop("client_id", None)
            d.pop("client_secret", None)
            d.pop("user_id", None)
        shops_list.append(d)
    return jsonify(shops_list)


@shops_bp.route("/api/shops", methods=["POST"])
@require_auth
@handle_errors
def create_shop():
    """Создать новый магазин (только админ и super_admin)"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return (
            jsonify({"error": "Access denied. Требуется роль admin или super_admin"}),
            403,
        )

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = (data.get("name") or "").strip()
    shop_url = (data.get("shop_url") or "").strip()
    api_key_value = data.get("api_key")
    api_key = api_key_value.strip() if api_key_value else None

    if not name or not shop_url:
        return jsonify({"error": "Name and shop_url are required"}), 400

    if not shop_url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid shop URL"}), 400

    try:
        with get_connection() as conn:
            cursor = conn.execute(
            """
            INSERT INTO avito_shops (name, shop_url, api_key, is_active)
            VALUES (?, ?, ?, ?)
        """,
            (name, shop_url, api_key, data.get("is_active", True)),
        )
        shop_id = cursor.lastrowid
            conn.commit()
            return jsonify({"success": True, "id": shop_id}), 201
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return jsonify({"error": "Shop with this URL already exists"}), 400
        return jsonify({"error": str(e)}), 400


@shops_bp.route("/api/shops/<int:shop_id>", methods=["GET"])
@require_auth
@handle_errors
def get_shop(shop_id):
    """Получить данные одного магазина"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return jsonify({"error": "Access denied"}), 403

    try:
        with get_connection() as conn:
            shop = conn.execute(
            """
            SELECT 
                *, 
                CASE 
                    WHEN client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL 
                    THEN 'ok' ELSE 'missing' 
                END AS avito_status
            FROM avito_shops 
            WHERE id = ?
        """,
            (shop_id,),
        ).fetchone()

        if not shop:
            return jsonify({"error": "Магазин не найден"}), 404

        return jsonify(dict(shop)), 200
    except Exception as e:
        logger.error(f"[GET SHOP] Ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@shops_bp.route("/api/shops/<int:shop_id>", methods=["PUT"])
@require_auth
@handle_errors
def update_shop(shop_id):
    """Обновить магазин"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400

    name = (data.get("name") or "").strip()
    shop_url = (data.get("shop_url") or "").strip()
    api_key_value = data.get("api_key")
    api_key = api_key_value.strip() if api_key_value else None
    is_active = data.get("is_active", True)

    if not name or not shop_url:
        return jsonify({"error": "Name and shop_url are required"}), 400

    if not shop_url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid shop URL"}), 400

    try:
        with get_connection() as conn:
            exists = conn.execute("SELECT id FROM avito_shops WHERE id = ?", (shop_id,)).fetchone()
            if not exists:
                return jsonify({"error": "Магазин не найден"}), 404

            conn.execute(
                """
                UPDATE avito_shops 
                SET name = ?, shop_url = ?, api_key = ?, is_active = ?
                WHERE id = ?
            """,
                (name, shop_url, api_key, is_active, shop_id),
            )
            conn.commit()
            return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"[UPDATE SHOP] Ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@shops_bp.route("/api/shops/<int:shop_id>/credentials", methods=["PUT"])
@require_auth
@handle_errors
def update_shop_credentials(shop_id):
    """Обновить OAuth ключи магазина (только админ и super_admin)"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return (
            jsonify({"error": "Access denied. Требуется роль admin или super_admin"}),
            403,
        )

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "No data provided"}), 400

    client_id = str(data.get("client_id") or "").strip()
    client_secret = str(data.get("client_secret") or "").strip()
    user_id = str(data.get("user_id") or "").strip()

    if not client_id or not client_secret or not user_id:
        return jsonify({"error": "client_id, client_secret и user_id обязательны"}), 400

    try:
        with get_connection() as conn:
            exists = conn.execute("SELECT id, name FROM avito_shops WHERE id = ?", (shop_id,)).fetchone()
            if not exists:
                return jsonify({"error": "Shop not found"}), 404

            cursor = conn.execute(
                """
                UPDATE avito_shops
                SET client_id = ?, client_secret = ?, user_id = ?, token_status = NULL, token_checked_at = NULL
                WHERE id = ?
            """,
                (client_id, client_secret, user_id, shop_id),
            )

            rows_affected = cursor.rowcount
            logger.info(f"[UPDATE CREDENTIALS] Обновлено строк: {rows_affected} для магазина {shop_id}")

            if rows_affected == 0:
                return jsonify({"error": "Магазин не найден"}), 404

            conn.commit()

        # Регистрируем webhook для магазина
        webhook_registered = False
            try:
                webhook_url = os.getenv("AVITO_WEBHOOK_URL", "https://osagaming.store/webhook/avito")
                logger.info(f"[UPDATE CREDENTIALS] Регистрация webhook для магазина {shop_id}: {webhook_url}")

                api = AvitoAPI(client_id=client_id, client_secret=client_secret)
                webhook_result = api.register_webhook_v3(url=webhook_url, types=["message", "chat"])

                if webhook_result:
                    conn.execute(
                        """
                        UPDATE avito_shops 
                        SET webhook_registered = 1 
                        WHERE id = ?
                    """,
                        (shop_id,),
                    )
                    conn.commit()
                    webhook_registered = True
                    logger.info(f"[UPDATE CREDENTIALS] Webhook успешно зарегистрирован для магазина {shop_id}")
            except Exception as webhook_err:
                logger.warning(
                    f"[UPDATE CREDENTIALS] Ошибка регистрации webhook: {webhook_err}",
                    exc_info=True,
                )

        # Синхронизируем чаты сразу после сохранения ключей
            sync_result = {"success": False, "synced_count": 0}
            try:
                from services.sync_service import sync_chats_from_avito

                logger.info(f"[UPDATE CREDENTIALS] Начинаем синхронизацию чатов для магазина {shop_id}")
                sync_result = sync_chats_from_avito(shop_id=shop_id)
                if sync_result.get("success"):
                    synced_count = sync_result.get("synced_count", 0)
                    logger.info(f"[UPDATE CREDENTIALS] Синхронизировано {synced_count} чатов для магазина {shop_id}")
            except Exception as sync_err:
                logger.warning(
                    f"[UPDATE CREDENTIALS] Ошибка синхронизации чатов: {sync_err}",
                    exc_info=True,
                )

        # Логируем действие
        try:
            log_activity(
                session.get("user_id"),
                "update_avito_credentials",
                f'Обновлены OAuth ключи для магазина ID: {shop_id} ({exists["name"]})',
                "shop",
                shop_id,
            )
        except Exception as log_err:
            logger.warning(f"[UPDATE CREDENTIALS] Не удалось залогировать действие: {log_err}")

        message = "Ключи успешно сохранены"
        if webhook_registered:
            message += ". Webhook зарегистрирован"
        if sync_result.get("success"):
            message += f'. Синхронизировано {sync_result.get("synced_count", 0)} чатов'

        return jsonify(
            {
                "success": True,
                "message": message,
                "webhook_registered": webhook_registered,
                "chats_synced": sync_result.get("synced_count", 0),
            }
        )
    except Exception as e:
        logger.error(f"[UPDATE CREDENTIALS] Ошибка сохранения ключей Avito: {e}", exc_info=True)
        return jsonify({"error": f"Ошибка сохранения: {str(e)}"}), 500


@shops_bp.route("/api/shops/analytics")
@require_auth
@require_role("admin")
@handle_errors
def shops_analytics():
    """Аналитика по магазинам"""
    with get_connection() as conn:
        data = conn.execute(
        """
        SELECT 
            s.id,
            s.name,
            s.is_active,
            s.token_status,
            s.webhook_registered,
            COUNT(c.id) as total_chats,
            SUM(CASE WHEN c.status = 'active' THEN 1 ELSE 0 END) as active_chats,
            SUM(CASE WHEN c.priority = 'urgent' THEN 1 ELSE 0 END) as urgent_chats,
            AVG(c.response_timer) as avg_response_timer,
            SUM(CASE WHEN c.unread_count > 0 THEN 1 ELSE 0 END) as chats_with_unread
        FROM avito_shops s
        LEFT JOIN avito_chats c ON c.shop_id = s.id
        GROUP BY s.id, s.name, s.is_active, s.token_status, s.webhook_registered
        ORDER BY s.name
    """
    ).fetchall()
    return jsonify([dict(row) for row in data])


@shops_bp.route("/api/shops/<int:shop_id>", methods=["DELETE"])
@require_auth
@handle_errors
def delete_shop(shop_id):
    """Удалить магазин (только админ и super_admin)"""
    user_role = session.get("user_role")
    if user_role not in ["admin", "super_admin"]:
        return (
            jsonify({"error": "Access denied. Требуется роль admin или super_admin"}),
            403,
        )

    try:
        with get_connection() as conn:
            shop = conn.execute("SELECT id, name FROM avito_shops WHERE id = ?", (shop_id,)).fetchone()
            if not shop:
                return jsonify({"error": "Shop not found"}), 404

            # Удаляем назначения менеджеров на этот магазин
            conn.execute("DELETE FROM manager_assignments WHERE shop_id = ?", (shop_id,))

            # Удаляем магазин
            conn.execute("DELETE FROM avito_shops WHERE id = ?", (shop_id,))
            conn.commit()

            log_activity(
                session["user_id"],
                "delete_shop",
                f'Удален магазин ID: {shop_id} ({shop["name"]})',
                "shop",
                shop_id,
            )

            return jsonify({"success": True, "message": "Магазин успешно удален"}), 200
    except Exception as e:
        logger.error(f"Ошибка удаления магазина: {e}", exc_info=True)
        return jsonify({"error": f"Ошибка удаления: {str(e)}"}), 400


@shops_bp.route("/api/shops/<int:shop_id>/assign", methods=["POST"])
@require_auth
@handle_errors
def assign_manager(shop_id):
    """Назначить менеджера на магазин"""
    if session.get("user_role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    manager_id = data.get("manager_id")

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO manager_assignments (manager_id, shop_id)
                VALUES (?, ?)
            """,
                (manager_id, shop_id),
            )
            conn.commit()
            return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@shops_bp.route("/api/shops/<int:shop_id>/stats")
@require_auth
@handle_errors
def get_shop_stats(shop_id):
    """Получить статистику по магазину"""
    with get_connection() as conn:
        stats = {
            "total_chats": conn.execute(
                "SELECT COUNT(*) as count FROM avito_chats WHERE shop_id = ?", (shop_id,)
            ).fetchone()["count"],
            "active_chats": conn.execute(
                'SELECT COUNT(*) as count FROM avito_chats WHERE shop_id = ? AND status = "active"',
                (shop_id,),
            ).fetchone()["count"],
            "urgent_chats": conn.execute(
                'SELECT COUNT(*) as count FROM avito_chats WHERE shop_id = ? AND priority = "urgent"',
                (shop_id,),
            ).fetchone()["count"],
        }
    return jsonify(stats)


@shops_bp.route("/api/shops/<int:shop_id>/avito/health")
@require_auth
@handle_errors
def avito_shop_health(shop_id):
    """Проверка доступности Avito OAuth для конкретного магазина"""
    with get_connection() as conn:
        shop = conn.execute(
            """
            SELECT id, name, client_id, client_secret, user_id
            FROM avito_shops
            WHERE id = ?
        """,
            (shop_id,),
        ).fetchone()

    if not shop:
        return jsonify({"error": "Shop not found"}), 404

    if not shop["client_id"] or not shop["client_secret"] or not shop["user_id"]:
        return jsonify({"status": "error", "message": "OAuth ключи не настроены"}), 400

    try:
        api = AvitoAPI(client_id=shop["client_id"], client_secret=shop["client_secret"])
        health = api.health_check()
        return jsonify(health)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@shops_bp.route("/api/shops/<int:shop_id>/managers")
@require_auth
@handle_errors
def get_shop_managers(shop_id):
    """Получить список менеджеров, назначенных на магазин"""
    with get_connection() as conn:
        managers = conn.execute(
            """
            SELECT u.id, u.username, u.email, u.role
            FROM users u
            JOIN manager_assignments ma ON u.id = ma.manager_id
            WHERE ma.shop_id = ?
        """,
            (shop_id,),
        ).fetchall()
    return jsonify([dict(m) for m in managers])


@shops_bp.route("/api/avito/test-send", methods=["POST"])
@require_auth
@require_role("admin")
@handle_errors
def avito_test_send():
    """Тестовая отправка сообщения через Avito API"""
    data = request.get_json() or {}
    shop_id = data.get("shop_id")
    chat_id = data.get("chat_id")
    message = data.get("message", "Тестовое сообщение")

    if not shop_id or not chat_id:
        return jsonify({"error": "shop_id and chat_id are required"}), 400

    with get_connection() as conn:
        shop = conn.execute(
            """
            SELECT client_id, client_secret, user_id
            FROM avito_shops
            WHERE id = ?
        """,
            (shop_id,),
        ).fetchone()

    if not shop or not shop["client_id"]:
        return jsonify({"error": "Shop not found or OAuth keys not configured"}), 404

    try:
        api = AvitoAPI(client_id=shop["client_id"], client_secret=shop["client_secret"])
        result = api.send_message(user_id=shop["user_id"], chat_id=chat_id, message=message)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
