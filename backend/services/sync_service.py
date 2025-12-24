"""
Сервис для синхронизации чатов с Avito API
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from avito_api import AvitoAPI
from database import get_connection

logger = logging.getLogger(__name__)


def sync_chats_from_avito(shop_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Синхронизация чатов из Avito API для всех магазинов или конкретного магазина

    Args:
        shop_id: ID магазина (если None, синхронизирует все магазины с ключами)

    Returns:
        Dict с результатами синхронизации
    """
    # Логируем путь к базе данных для диагностики
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "osagaming_crm.db")
    logger.info(f"[SYNC] Используется база данных: {db_path}")
    logger.info(f"[SYNC] База данных существует: {os.path.exists(db_path)}")

    with get_connection() as conn:
        synced_count = 0
        errors = []

        try:
        # Получаем магазины с настроенными ключами
        if shop_id:
            shops = conn.execute(
                """
                SELECT id, name, client_id, client_secret, user_id, is_active, shop_url
                FROM avito_shops 
                WHERE id = ? AND is_active = 1 AND client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL
            """,
                (shop_id,),
            ).fetchall()
        else:
            shops = conn.execute(
                """
                SELECT id, name, client_id, client_secret, user_id, is_active, shop_url
                FROM avito_shops 
                WHERE is_active = 1 AND client_id IS NOT NULL AND client_secret IS NOT NULL AND user_id IS NOT NULL
            """
            ).fetchall()

        logger.info(f"[SYNC] Найдено магазинов для синхронизации: {len(shops)}")
        if shops:
            shop_names = [shop["name"] for shop in shops]
            logger.info(f"[SYNC] Магазины: {', '.join(shop_names)}")

        for idx, shop in enumerate(shops):
            shop = dict(shop)
            logger.info(f"[SYNC] ========== Начало синхронизации магазина {shop['id']}: {shop['name']} ==========")

            # Добавляем задержку между запросами к разным магазинам
            if idx > 0:
                time.sleep(2)

            try:
                api = AvitoAPI(shop["client_id"], shop["client_secret"], shop_id=str(shop["id"]))

                # Получаем чаты из Avito API с пагинацией
                offset = 0
                limit = 100
                total_synced = 0

                while True:
                    try:
                        response = api.get_chats(user_id=str(shop["user_id"]), limit=limit, offset=offset)

                        # Обрабатываем ответ API (подробная логика из app.py)
                        if isinstance(response, dict):
                            chats_data = response.get("chats", [])
                            if not chats_data:
                                chats_data = response.get("items", [])
                            if not chats_data and "data" in response:
                                data = response["data"]
                                if isinstance(data, dict):
                                    chats_data = data.get("chats", []) or data.get("items", [])
                                elif isinstance(data, list):
                                    chats_data = data
                        elif isinstance(response, list):
                            chats_data = response
                        else:
                            chats_data = []

                        chats_count = len(chats_data) if isinstance(chats_data, list) else 0
                        logger.info(f"[SYNC] Извлечено чатов: {chats_count}")

                        if not chats_data or chats_count == 0:
                            logger.info("[SYNC] Нет чатов для обработки, завершаем пагинацию")
                            break

                        # Обрабатываем каждый чат (упрощенная версия из app.py)
                        for chat_idx, chat_data in enumerate(chats_data):
                            try:
                                avito_chat_id = chat_data.get("id")
                                if not avito_chat_id:
                                    continue

                                avito_chat_id_str = str(avito_chat_id)

                                # Проверяем существование чата
                                existing = conn.execute(
                                    "SELECT id, shop_id, chat_id FROM avito_chats WHERE shop_id = ? AND chat_id = ?",
                                    (shop["id"], avito_chat_id_str),
                                ).fetchone()

                                if existing:
                                    existing = dict(existing)

                                # Получаем данные чата
                                users_data = chat_data.get("users", [])
                                if isinstance(users_data, list) and len(users_data) > 0:
                                    user_info = users_data[0] if isinstance(users_data[0], dict) else {}
                                elif isinstance(users_data, dict):
                                    user_info = users_data
                                else:
                                    user_info = {}

                                client_name = user_info.get("name") or user_info.get("profile", {}).get(
                                    "name", "Неизвестно"
                                )
                                client_phone = user_info.get("phone") or user_info.get("profile", {}).get("phone", "")
                                customer_id = user_info.get("id") or user_info.get("profile", {}).get("id", "")

                                # Получаем последнее сообщение
                                last_message_data = chat_data.get("last_message", {})
                                if isinstance(last_message_data, dict):
                                    if "content" in last_message_data:
                                        content = last_message_data["content"]
                                        if isinstance(content, dict):
                                            last_message = content.get("text", "") or content.get("message", "")
                                        else:
                                            last_message = str(content)
                                    else:
                                        last_message = last_message_data.get("text", "") or last_message_data.get(
                                            "message", ""
                                        )
                                else:
                                    last_message = ""

                                # Получаем product_url из context.value
                                product_url = None
                                context = chat_data.get("context", {})
                                if isinstance(context, dict):
                                    item_data = (
                                        context.get("value")
                                        or context.get("item")
                                        or context.get("listing")
                                        or context.get("ad", {})
                                    )
                                else:
                                    item_data = chat_data.get(
                                        "item",
                                        chat_data.get("listing", chat_data.get("ad", {})),
                                    )

                                listing_data_json = None
                                if isinstance(item_data, dict) and item_data:
                                    listing_data_json = json.dumps(item_data, ensure_ascii=False)
                                    item_id = item_data.get("id")
                                    product_url = (
                                        item_data.get("url")
                                        or item_data.get("link")
                                        or item_data.get("href")
                                        or item_data.get("value")
                                        or item_data.get("uri")
                                    )

                                    if not product_url and item_id:
                                        item_id_str = str(item_id)
                                        shop_url_part = (
                                            shop.get("shop_url", "").split("/")[-1] if shop.get("shop_url") else ""
                                        )
                                        if shop_url_part:
                                            product_url = f"https://www.avito.ru/{shop_url_part}/items/{item_id_str}"
                                        else:
                                            product_url = f"https://www.avito.ru/items/{item_id_str}"

                                    if product_url and isinstance(product_url, str):
                                        if product_url.startswith("/"):
                                            product_url = f"https://www.avito.ru{product_url}"
                                        elif not product_url.startswith("http"):
                                            shop_url_part = (
                                                shop.get("shop_url", "").split("/")[-1] if shop.get("shop_url") else ""
                                            )
                                            if shop_url_part:
                                                product_url = (
                                                    f"https://www.avito.ru/{shop_url_part}/items/{product_url}"
                                                )
                                            else:
                                                product_url = f"https://www.avito.ru/items/{product_url}"

                                if not product_url:
                                    product_url = (
                                        chat_data.get("item_url")
                                        or chat_data.get("listing_url")
                                        or chat_data.get("ad_url")
                                        or chat_data.get("product_url")
                                    )

                                unread_count = chat_data.get("unread_count", 0) or chat_data.get("unreadCount", 0)
                                is_blocked = chat_data.get("is_blocked", False) or chat_data.get("isBlocked", False)
                                is_archived = chat_data.get("is_archived", False) or chat_data.get("isArchived", False)

                                status = "archived" if is_archived else "active"
                                if is_blocked:
                                    status = "blocked"

                                priority = "normal"
                                if last_message_data and isinstance(last_message_data, dict):
                                    last_message_time = last_message_data.get("created") or last_message_data.get(
                                        "created_at"
                                    )
                                    if last_message_time:
                                        try:
                                            if isinstance(last_message_time, (int, float)):
                                                msg_time = datetime.fromtimestamp(last_message_time)
                                            else:
                                                msg_time = datetime.fromisoformat(
                                                    str(last_message_time).replace("Z", "+00:00")
                                                )
                                            time_diff = datetime.now() - msg_time
                                            if time_diff.total_seconds() < 3600:
                                                priority = "urgent"
                                            elif time_diff.total_seconds() < 86400:
                                                priority = "new"
                                        except Exception:
                                            pass

                                if existing:
                                    existing = dict(existing) if not isinstance(existing, dict) else existing
                                    existing_id = existing.get("id")

                                    update_fields = [
                                        "client_name = ?",
                                        "client_phone = ?",
                                        "customer_id = ?",
                                        "product_url = ?",
                                        "last_message = ?",
                                        "unread_count = ?",
                                        "status = ?",
                                        "priority = ?",
                                        "updated_at = CURRENT_TIMESTAMP",
                                    ]
                                    update_values = [
                                        client_name,
                                        client_phone,
                                        customer_id if customer_id else None,
                                        product_url if product_url else None,
                                        last_message,
                                        unread_count,
                                        status,
                                        priority,
                                    ]

                                    if listing_data_json:
                                        update_fields.append("listing_data = ?")
                                        update_values.append(listing_data_json)

                                    update_values.append(existing_id)

                                    conn.execute(
                                        f"""
                                        UPDATE avito_chats 
                                        SET {', '.join(update_fields)}
                                        WHERE id = ?
                                    """,
                                        tuple(update_values),
                                    )
                                    total_synced += 1
                                else:
                                    insert_fields = [
                                        "shop_id",
                                        "chat_id",
                                        "customer_id",
                                        "client_name",
                                        "client_phone",
                                        "product_url",
                                        "last_message",
                                        "unread_count",
                                        "status",
                                        "priority",
                                        "created_at",
                                        "updated_at",
                                    ]
                                    insert_values = [
                                        shop["id"],
                                        avito_chat_id_str,
                                        customer_id if customer_id else None,
                                        client_name,
                                        client_phone,
                                        product_url if product_url else None,
                                        last_message,
                                        unread_count,
                                        status,
                                        priority,
                                    ]

                                    if listing_data_json:
                                        insert_fields.append("listing_data")
                                        insert_values.append(listing_data_json)

                                    placeholders = ["?" for _ in insert_values]
                                    placeholders.append("CURRENT_TIMESTAMP")
                                    placeholders.append("CURRENT_TIMESTAMP")

                                    cursor = conn.execute(
                                        f"""
                                        INSERT INTO avito_chats 
                                            ({', '.join(insert_fields)}, created_at, updated_at)
                                        VALUES ({', '.join(placeholders)})
                                    """,
                                        tuple(insert_values),
                                    )
                                    total_synced += 1

                            except Exception as chat_error:
                                logger.error(
                                    f"[SYNC] Ошибка синхронизации чата: {chat_error}",
                                    exc_info=True,
                                )
                                errors.append(f"Chat sync error: {str(chat_error)}")

                        conn.commit()

                        # Проверяем метаданные для пагинации
                        has_more = False
                        if isinstance(response, dict) and "meta" in response:
                            has_more = response["meta"].get("has_more", False)

                        if chats_count < limit and not has_more:
                            break
                        elif chats_count == 0 and not has_more:
                            break

                        if offset >= 1000:
                            logger.warning(f"[SYNC] Достигнут лимит offset={offset}, завершаем пагинацию")
                            break

                        offset += limit

                    except Exception as e:
                        error_str = str(e)
                        if "403" in error_str or "Forbidden" in error_str:
                            logger.warning(f"[SYNC] ⚠️  Магазин {shop['id']} ({shop['name']}): 403 Forbidden")
                            errors.append(f"Магазин {shop['name']}: 403 Forbidden")
                        else:
                            logger.error(f"[SYNC] Ошибка получения чатов для магазина {shop['name']}: {error_str}")
                            errors.append(f"Ошибка получения чатов для магазина {shop['name']}: {error_str}")
                        break

                synced_count += total_synced
                conn.commit()
                logger.info(f"[SYNC] ✅ Магазин {shop['id']} ({shop['name']}) синхронизирован: {total_synced} чатов")

            except Exception as shop_error:
                error_str = str(shop_error)
                if "403" in error_str or "Forbidden" in error_str:
                    error_msg = f"Магазин {shop['name']}: 403 Forbidden"
                else:
                    error_msg = f"Ошибка синхронизации магазина {shop['name']}: {error_str}"
                logger.error(f"[SYNC] ❌ {error_msg}", exc_info=True)
                errors.append(error_msg)

        # Автоматически обновляем таймеры для всех чатов после синхронизации
        try:
            logger.info("[SYNC] 🔄 Начинаем обновление таймеров для всех чатов...")
            from services.messenger_service import MessengerService

            service = MessengerService(conn, None)
            timer_result = service.update_all_response_timers()
            logger.info(
                f"[SYNC] ✅ Таймеры обновлены: обновлено={timer_result['updated']}, ошибок={timer_result['errors']}"
            )
        except Exception as timer_update_error:
            logger.warning(f"[SYNC] ⚠️ Ошибка обновления таймеров: {timer_update_error}")

        # Автоматически завершаем старые чаты
        try:
            logger.info("[SYNC] 🔄 Начинаем автозавершение старых чатов...")
            from services.messenger_service import MessengerService

            service = MessengerService(conn, None)
            complete_result = service.auto_complete_old_chats(days=1)
            logger.info(
                f"[SYNC] ✅ Автозавершение завершено: завершено={complete_result['completed']}, ошибок={complete_result['errors']}"
            )
        except Exception as auto_complete_error:
            logger.warning(f"[SYNC] ⚠️ Ошибка автозавершения чатов: {auto_complete_error}")

        logger.info("[SYNC] ========== Синхронизация завершена ==========")
        logger.info(f"[SYNC] Всего синхронизировано чатов: {synced_count}")
        logger.info(f"[SYNC] Обработано магазинов: {len(shops)}")
        if errors:
            logger.warning(f"[SYNC] Ошибок: {len(errors)}")

        return {
            "success": True,
            "synced_count": synced_count,
            "errors": errors if errors else None,
        }

    except Exception as e:
        logger.error(f"[SYNC] Критическая ошибка синхронизации: {e}", exc_info=True)
        return {"success": False, "error": str(e), "synced_count": synced_count}
