"""
Маршруты для отображения страниц
"""

from auth import get_user_by_id
from flask import Blueprint, render_template, session
from utils.decorators import handle_errors, require_auth

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/chats")
@require_auth
@handle_errors
def chats_page():
    """Страница чатов"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("chats.html", user=user)


@pages_bp.route("/shops")
@require_auth
@handle_errors
def shops_page():
    """Страница магазинов"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("shops.html", user=user)


@pages_bp.route("/deliveries")
@require_auth
@handle_errors
def deliveries_page():
    """Страница доставок"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("deliveries.html", user=user)


@pages_bp.route("/analytics")
@require_auth
@handle_errors
def analytics_page():
    """Страница аналитики"""
    user = get_user_by_id(session.get("user_id"))
    # Импортируем функцию получения статистики
    from app import get_system_stats

    stats = get_system_stats()
    return render_template("analytics.html", user=user, stats=stats)


@pages_bp.route("/buyout")
@require_auth
@handle_errors
def buyout_page():
    """Страница выкупа"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("buyout.html", user=user)


@pages_bp.route("/settings")
@require_auth
@handle_errors
def settings_page():
    """Страница настроек"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("settings.html", user=user)


@pages_bp.route("/managers")
@require_auth
@handle_errors
def managers_page():
    """Страница управления менеджерами"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("managers.html", user=user)


@pages_bp.route("/system-logs")
@require_auth
@handle_errors
def system_logs_page():
    """Страница системных логов"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("system_logs.html", user=user)


@pages_bp.route("/quick-replies")
@require_auth
@handle_errors
def quick_replies_page():
    """Страница быстрых ответов"""
    user = get_user_by_id(session.get("user_id"))
    return render_template("quick_replies.html", user=user)
