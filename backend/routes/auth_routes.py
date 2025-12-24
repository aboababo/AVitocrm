"""
Маршруты для аутентификации и авторизации
"""

from datetime import datetime

from auth import authenticate_user, get_user_by_id, update_user_password
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
)
from utils.decorators import handle_errors, require_auth, require_role
from utils.helpers import get_system_stats, log_activity
from utils.validators import validate_email

auth_bp = Blueprint("auth", __name__)

# Импорт rate limiter если доступен
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    limiter = None


@auth_bp.route("/")
def home():
    """Главная страница - редирект на дашборд"""
    if "user_id" in session:
        user = get_user_by_id(session["user_id"])
        if user["role"] == "admin":
            return redirect("/admin/dashboard")
        else:
            return redirect("/manager/dashboard")
    return redirect("/login")


@auth_bp.route("/change-password", methods=["GET", "POST"])
@require_auth
@handle_errors
def change_password():
    """Страница смены пароля (для новых пользователей)"""
    user = get_user_by_id(session["user_id"])
    if not user:
        return redirect("/login")

    # Проверяем, это первый вход (нужно ли требовать текущий пароль)
    password_changed = user.get("password_changed")
    is_first_login = password_changed is not True

    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not new_password or not confirm_password:
            return render_template(
                "change_password.html",
                error="Заполните все поля",
                hide_header=True,
                is_first_login=is_first_login,
            )

        if new_password != confirm_password:
            return render_template(
                "change_password.html",
                error="Пароли не совпадают",
                hide_header=True,
                is_first_login=is_first_login,
            )

        if len(new_password) < 6:
            return render_template(
                "change_password.html",
                error="Пароль должен быть не менее 6 символов",
                hide_header=True,
                is_first_login=is_first_login,
            )

        # Проверяем текущий пароль только если это не первый вход
        if not is_first_login:
            auth_result = authenticate_user(user["email"], current_password)
            if not auth_result:
                return render_template(
                    "change_password.html",
                    error="Текущий пароль неверен",
                    hide_header=True,
                    is_first_login=is_first_login,
                )

        # Обновляем пароль
        if update_user_password(session["user_id"], new_password):
            # Логируем изменение пароля
            log_activity(
                session["user_id"],
                "change_password",
                ("Пользователь изменил пароль при первом входе" if is_first_login else "Пользователь изменил пароль"),
                "user",
                session["user_id"],
            )

            flash("Пароль успешно изменен!")
            # Перенаправляем на соответствующую панель
            if user["role"] == "super_admin" or user["role"] == "admin":
                return redirect("/admin/dashboard")
            else:
                return redirect("/manager/dashboard")
        else:
            return render_template(
                "change_password.html",
                error="Ошибка изменения пароля",
                hide_header=True,
                is_first_login=is_first_login,
            )

    return render_template("change_password.html", hide_header=True, is_first_login=is_first_login)


@auth_bp.route("/login", methods=["GET", "POST"])
@handle_errors
def login():
    """Страница входа"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Валидация
        if not email or not password:
            return render_template("login.html", error="Заполните все поля", hide_header=True)

        if not validate_email(email):
            return render_template("login.html", error="Неверный формат email", hide_header=True)

        user = authenticate_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_role"] = user["role"]
            session["login_time"] = datetime.now().isoformat()
            session.permanent = True  # Делаем сессию постоянной (живет 7 дней согласно PERMANENT_SESSION_LIFETIME)

            # Проверяем, нужно ли менять пароль (первый вход или одноразовый пароль)
            temp_password_used = user.get("temp_password_used", False)
            password_changed = user.get("password_changed", True)

            if temp_password_used or not password_changed:
                # Перенаправляем на страницу смены пароля
                return redirect("/change-password")

            # Логируем вход
            log_activity(user["id"], "login", "Вход в систему", "user", user["id"])

            if user["role"] == "super_admin":
                return redirect("/admin/dashboard")
            elif user["role"] == "admin":
                return redirect("/admin/dashboard")
            else:
                return redirect("/manager/dashboard")
        else:
            return render_template("login.html", error="Неверный email или пароль", hide_header=True)

    return render_template("login.html", hide_header=True)


@auth_bp.route("/logout")
def logout():
    """Выход из системы"""
    session.clear()
    return redirect("/login")


@auth_bp.route("/admin/dashboard")
@require_auth
@require_role("admin")
@handle_errors
def admin_dashboard():
    """Админ панель"""
    user = get_user_by_id(session["user_id"])
    stats = get_system_stats()
    return render_template("admin_dashboard.html", user=user, stats=stats)


@auth_bp.route("/manager/dashboard")
@require_auth
@handle_errors
def manager_dashboard():
    """Панель менеджера"""
    user = get_user_by_id(session["user_id"])
    stats = get_system_stats()
    return render_template("manager_dashboard.html", user=user, stats=stats)
