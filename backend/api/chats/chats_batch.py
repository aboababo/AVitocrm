"""
Batch операции для чатов
"""

import logging
from functools import wraps

from flask import Blueprint, jsonify, request, session
from services.sync_service import sync_chats_from_avito

logger = logging.getLogger("app")

batch_bp = Blueprint("chats_batch", __name__, url_prefix="/api/chats")


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


@batch_bp.route("/sync", methods=["POST"])
@require_auth
@handle_errors
def sync_chats():
    """Синхронизация чатов с Avito API"""
    data = request.get_json() or {}
    shop_id = data.get("shop_id")

    result = sync_chats_from_avito(shop_id=shop_id)

    if result.get("success"):
        synced_count = result.get("synced_count", 0)
        logger.info(f"[SYNC] Синхронизировано {synced_count} чатов")
        return (
            jsonify(
                {
                    "success": True,
                    "synced_count": synced_count,
                    "message": f"Синхронизировано {synced_count} чатов",
                }
            ),
            200,
        )
    else:
        error = result.get("error", "Unknown error")
        logger.error(f"[SYNC] Ошибка синхронизации: {error}")
        return jsonify({"success": False, "error": error}), 500
