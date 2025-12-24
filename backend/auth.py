"""
OSAGAMING CRM - Модуль аутентификации и авторизации
==================================================

Этот файл содержит функции для:
- Хеширования и проверки паролей
- Аутентификации пользователей
- Получения информации о пользователях
- Работы с настройками пользователей

Безопасность:
- Пароли хранятся в виде bcrypt хешей (с солью)
- Поддержка миграции старых SHA256 хешей
- Проверка активности аккаунта перед аутентификацией
- Защита от SQL инъекций через параметризованные запросы

Автор: OSAGAMING Development Team
Версия: 3.0
"""

import hashlib
import re
import secrets
import string

import bcrypt
from database import get_connection


def hash_password(password: str) -> str:
    """
    Хеширование пароля с использованием bcrypt (с солью)

    Преобразует пароль в хеш для безопасного хранения в базе данных.
    Пароли никогда не хранятся в открытом виде.
    Каждый хеш содержит уникальную соль, что защищает от rainbow table атак.

    Алгоритм: bcrypt (с автоматической генерацией соли)

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Хеш пароля для хранения в БД

    Пример:
        hash_password("mypassword123")
        -> "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY..."

    Примечание:
        bcrypt - это односторонняя функция с солью, нельзя восстановить пароль из хеша.
        Для проверки используется bcrypt.checkpw().
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def is_old_password_hash(hashed: str) -> bool:
    """
    Проверяет, является ли хеш старым SHA256 форматом

    Args:
        hashed: Хеш для проверки

    Returns:
        bool: True если это старый SHA256 хеш
    """
    # SHA256 хеш - это 64 символа hex (допустим регистр и возможные пробелы вокруг)
    if not isinstance(hashed, str):
        return False
    s = hashed.strip()
    # Допускаем 63 или 64 hex-символа — некоторые старые хеши могут терять ведущий ноль
    return re.fullmatch(r"[0-9a-fA-F]{63,64}", s) is not None


def migrate_password_on_login(user_id: int, password: str, old_hash: str) -> bool:
    """
    Мигрирует старый SHA256 хеш на bcrypt при следующем входе

    Args:
        user_id: ID пользователя
        password: Пароль в открытом виде
        old_hash: Старый SHA256 хеш

    Returns:
        bool: True если миграция успешна
    """
    # Проверяем старый формат
    if is_old_password_hash(old_hash):
        # Проверяем старый пароль
        if hashlib.sha256(password.encode()).hexdigest() == old_hash:
            # Обновляем на новый формат
            from database import get_connection

            with get_connection() as conn:
                new_hash = hash_password(password)
                conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))
                conn.commit()
            return True
    return False


def generate_temp_password(length=12):
    """
    Генерация одноразового пароля для новых менеджеров

    Создает безопасный одноразовый пароль из букв, цифр и символов.

    Args:
        length (int): Длина пароля (по умолчанию 12)

    Returns:
        str: Одноразовый пароль
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for i in range(length))


def update_user_password(user_id, new_password):
    """
    Обновление пароля пользователя

    Args:
        user_id (int): ID пользователя
        new_password (str): Новый пароль

    Returns:
        bool: True если успешно
    """
    from database import get_connection

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET password = ?, temp_password = NULL, password_changed = 1
                WHERE id = ?
            """,
                (hash_password(new_password), user_id),
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка обновления пароля: {e}")
        return False


def verify_password(password: str, hashed: str) -> bool:
    """
    Проверка пароля

    Поддерживает как новый формат (bcrypt), так и старый (SHA256) для миграции.

    Args:
        password: Пароль для проверки (в открытом виде)
        hashed: Хранящийся хеш пароля из базы данных

    Returns:
        bool: True если пароль верен

    Пример:
        verify_password("mypassword", "$2b$12$...") -> True
        verify_password("wrongpass", "$2b$12$...") -> False
    """
    # Проверяем новый формат (bcrypt)
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    # Поддержка старого формата (SHA256) для миграции
    if is_old_password_hash(hashed):
        return hashlib.sha256(password.encode()).hexdigest() == hashed

    return False


def authenticate_user(email, password):
    """
    Аутентификация пользователя по email и паролю

    Поддерживает одноразовые пароли для новых менеджеров.
    При первом входе менеджер должен изменить пароль.

    Процесс:
        1. Поиск пользователя по email и проверяем активность
        2. Проверка правильности пароля (основной или одноразовый)
        3. Возврат данных пользователя с флагом необходимости смены пароля

    Args:
        email (str): Email адрес пользователя
        password (str): Пароль пользователя

    Returns:
        dict: Словарь с данными пользователя при успешной аутентификации
        None: Если пользователь не найден, неактивен или пароль неверен

    Словарь содержит:
        - Все поля пользователя из БД
        - 'temp_password_used': True если использован одноразовый пароль
    """
    with get_connection() as conn:
        # Проверяем наличие колонок first_name и last_name
        try:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            has_first_name = "first_name" in columns
            has_last_name = "last_name" in columns
        except Exception:
            has_first_name = False
            has_last_name = False

    # Формируем запрос в зависимости от наличия колонок
    base_fields = "id, username, email, password, role, is_active, salary, kpi_score, temp_password, password_changed, created_at, created_by, settings"
    if has_first_name:
        base_fields += ", first_name"
    if has_last_name:
        base_fields += ", last_name"

    query = f"SELECT {base_fields} FROM users WHERE email = ? AND is_active = 1"

    # Ищем пользователя по email и проверяем активность
    with get_connection() as conn:
        user = conn.execute(query, (email,)).fetchone()

        if not user:
            return None

        user_dict = dict(user)
    # Добавляем значения по умолчанию для полей, которых может не быть
    if not has_first_name:
        user_dict["first_name"] = None
    if not has_last_name:
        user_dict["last_name"] = None

    # Проверяем основной пароль
    if verify_password(password, user_dict["password"]):
        # Если это старый формат пароля, мигрируем его
        if is_old_password_hash(user_dict["password"]):
            migrate_password_on_login(user_dict["id"], password, user_dict["password"])
            # Обновляем данные пользователя после миграции
            with get_connection() as conn:
                user = conn.execute(query, (email,)).fetchone()
                if user:
                    user_dict = dict(user)
                    if not has_first_name:
                        user_dict["first_name"] = None
                    if not has_last_name:
                        user_dict["last_name"] = None
        pass  # Основной пароль верен
    # Проверяем одноразовый пароль (если он есть и менеджер еще не изменил пароль)
    elif (
        user_dict.get("temp_password")
        and user_dict["temp_password"] == password
        and not user_dict.get("password_changed", False)
    ):
        user_dict["temp_password_used"] = True
    else:
        # Соединение глобальное, не закрываем
        return None

    return user_dict


def get_user_by_id(user_id):
    """
    Получение информации о пользователе по его ID

    Используется для получения данных пользователя из сессии или
    для отображения информации о других пользователях.

    Args:
        user_id (int): ID пользователя в базе данных

    Returns:
        dict: Словарь с данными пользователя:
            {
                'id': int,
                'username': str,
                'email': str,
                'role': str,
                'is_active': bool,
                'kpi_score': float,
                'password_changed': bool
            }
        None: Если пользователь не найден

    Пример:
        user = get_user_by_id(1)
        if user:
            print(f"Пользователь: {user['username']}, Роль: {user['role']}")

    Примечание:
        Не возвращает пароль и другие чувствительные данные для безопасности
    """
    from database import get_connection

    with get_connection() as conn:
        # Выбираем только необходимые поля (без пароля)
        user = conn.execute(
            "SELECT id, username, email, role, is_active, kpi_score, password_changed FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        # Преобразуем в словарь или возвращаем None
        return dict(user) if user else None


def get_user_settings(user_id):
    """
    Получение настроек пользователя

    Возвращает персональные настройки пользователя (тема, уведомления и т.д.)

    Args:
        user_id (int): ID пользователя

    Returns:
        dict: Словарь с настройками пользователя:
            {
                'id': int,
                'user_id': int,
                'theme': str,  # 'dark' или 'light'
                'colors': str,  # JSON строка с цветами
                'sound_alerts': bool,
                'push_notifications': bool
            }
        None: Если настройки не найдены

    Пример:
        settings = get_user_settings(1)
        if settings:
            print(f"Тема: {settings['theme']}")
    """
    from database import get_connection

    with get_connection() as conn:
        # Получаем все настройки пользователя
        settings = conn.execute(
            "SELECT id, user_id, theme, colors, sound_alerts, push_notifications, tab_visibility FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        # Преобразуем в словарь или возвращаем None
        return dict(settings) if settings else None
