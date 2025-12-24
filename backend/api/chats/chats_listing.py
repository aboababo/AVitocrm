"""
Операции с объявлениями (listings) для чатов
"""

import json
import logging
from functools import wraps

from database import get_db_connection
from flask import Blueprint, jsonify, session

logger = logging.getLogger("app")

listing_bp = Blueprint("chats_listing", __name__, url_prefix="/api/chats")


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


@listing_bp.route("/extract-product-urls", methods=["POST"])
@require_auth
@handle_errors
def extract_all_product_urls():
    """Извлечь product_url для всех чатов из сообщений"""
    conn = get_db_connection()

    try:
        # Получаем все чаты без product_url
        chats = conn.execute(
            """
            SELECT id, chat_id, shop_id
            FROM avito_chats
            WHERE product_url IS NULL OR product_url = ''
        """
        ).fetchall()

        extracted_count = 0
        errors = []

        for chat in chats:
            try:
                chat_id = chat["id"]
                chat.get("chat_id")
                shop_id = chat.get("shop_id")

                # Получаем информацию о магазине
                shop = conn.execute(
                    """
                    SELECT client_id, client_secret, user_id
                    FROM avito_shops
                    WHERE id = ?
                """,
                    (shop_id,),
                ).fetchone()

                if not shop or not shop.get("client_id") or not shop.get("client_secret"):
                    continue

                shop = dict(shop)

                # Пытаемся извлечь product_url из сообщений
                product_url = extract_product_url_from_messages(chat_id)

                if product_url:
                    conn.execute(
                        """
                        UPDATE avito_chats
                        SET product_url = ?
                        WHERE id = ?
                    """,
                        (product_url, chat_id),
                    )
                    extracted_count += 1
                    logger.info(f"[EXTRACT] Извлечен product_url для чата {chat_id}: {product_url}")

            except Exception as e:
                errors.append(f"Chat {chat['id']}: {str(e)}")
                logger.error(f"[EXTRACT] Ошибка для чата {chat['id']}: {e}")

        conn.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "extracted_count": extracted_count,
                    "errors": errors if errors else None,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"[EXTRACT] Критическая ошибка: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def extract_product_url_from_messages(chat_id):
    """Извлечь product_url из сообщений чата"""
    conn = get_db_connection()

    try:
        # Получаем последние сообщения чата
        messages = conn.execute(
            """
            SELECT message_text, metadata
            FROM avito_messages
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """,
            (chat_id,),
        ).fetchall()

        for message in messages:
            message_text = message.get("message_text", "")
            metadata = message.get("metadata")

            # Пытаемся найти URL в тексте сообщения
            import re

            url_pattern = r"https?://(?:www\.)?avito\.ru/[^\s]+"
            urls = re.findall(url_pattern, message_text)

            if urls:
                # Фильтруем только URL объявлений
                for url in urls:
                    if "/items/" in url or "/avito/" in url:
                        return url

            # Пытаемся извлечь из metadata
            if metadata:
                try:
                    metadata_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    if isinstance(metadata_dict, dict):
                        product_url = metadata_dict.get("product_url") or metadata_dict.get("item_url")
                        if product_url:
                            return product_url
                except:
                    pass

        return None
    except Exception as e:
        logger.error(f"[EXTRACT] Ошибка извлечения URL из сообщений: {e}")
        return None


@listing_bp.route("/<int:chat_id>/extract-product-url", methods=["POST"])
@require_auth
@handle_errors
def extract_product_url_from_messages_endpoint(chat_id):
    """Извлечь product_url для конкретного чата из сообщений"""
    product_url = extract_product_url_from_messages(chat_id)

    if product_url:
        conn = get_db_connection()
        conn.execute(
            """
            UPDATE avito_chats
            SET product_url = ?
            WHERE id = ?
        """,
            (product_url, chat_id),
        )
        conn.commit()

        return jsonify({"success": True, "product_url": product_url}), 200
    else:
        return (
            jsonify({"success": False, "message": "Product URL not found in messages"}),
            404,
        )
