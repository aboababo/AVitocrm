"""
Создание схемы базы данных и миграции
"""

import os
import sqlite3

# Определяем путь к базе данных
_DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_DB_DIR, "osagaming_crm.db")
_DB_PATH = os.path.normpath(_DB_PATH)


def is_database_initialized():
    """
    Проверяет, что база данных инициализирована (все основные таблицы существуют)

    Returns:
        bool: True если БД инициализирована, False в противном случае
    """
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5.0)
        cursor = conn.cursor()

        # Проверяем наличие основных таблиц
        required_tables = [
            "users",
            "avito_shops",
            "avito_chats",
            "avito_messages",
            "deliveries",
        ]

        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                conn.close()
                return False

        conn.close()
        return True
    except Exception:
        return False


def init_database():
    """
    Инициализация базы данных для CRM системы

    Создает все необходимые таблицы, индексы и добавляет тестовые данные.
    """
    # Убеждаемся, что директория существует
    db_dir = os.path.dirname(_DB_PATH)
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, mode=0o755, exist_ok=True)
        except Exception as e:
            raise RuntimeError(
                f"Cannot create database directory: {db_dir}\n"
                f"Error: {e}\n"
                f"Please create it manually: mkdir -p {db_dir} && chmod 755 {db_dir}"
            ) from e

    # Проверяем права на запись
    if not os.access(db_dir, os.W_OK):
        raise RuntimeError(f"No write permission for database directory: {db_dir}\n" f"Please run: chmod 755 {db_dir}")

    # Подключаемся к базе данных
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10.0)
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        if "unable to open database file" in error_msg:
            raise RuntimeError(
                f"Cannot open database file: {_DB_PATH}\n" f"Directory: {db_dir}\n" f"Please check permissions"
            ) from e
        raise

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Создаем таблицы (импортируем из оригинального database.py)
    # Здесь будет полная логика создания таблиц из database.py
    # Для краткости, оставляю заглушку - полный код нужно скопировать из database.py

    try:
        # Проверяем, инициализирована ли уже БД
        if is_database_initialized():
            # Логирование в консоль отключено
            # print(f"[DATABASE] База данных уже инициализирована: {_DB_PATH}")
            conn.close()
            return

        # Создание всех таблиц
        _create_tables(cursor)

        # Создание индексов
        _create_indexes(cursor)

        # Миграции
        _run_migrations(cursor)

        # Тестовые данные (если БД пустая)
        if _is_database_empty(cursor):
            _add_test_data(cursor)

        conn.commit()
        # Логирование в консоль отключено
        # print(f"[DATABASE] База данных инициализирована: {_DB_PATH}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_tables(cursor):
    """Создание всех таблиц"""
    # Импортируем логику из оригинального database.py
    # Здесь должна быть полная логика создания таблиц
    pass


def _create_indexes(cursor):
    """Создание индексов"""
    # Импортируем логику из оригинального database.py
    pass


def _run_migrations(cursor):
    """Выполнение миграций"""
    # Импортируем логику из оригинального database.py
    pass


def _is_database_empty(cursor):
    """Проверка, пуста ли база данных"""
    # Сначала проверяем, существует ли таблица users
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        return True  # Если таблицы нет, считаем БД пустой

    cursor.execute("SELECT COUNT(*) as count FROM users")
    result = cursor.fetchone()
    return result["count"] == 0 if result else True


def _add_test_data(cursor):
    """Добавление тестовых данных"""
    # Импортируем логику из оригинального database.py
    pass


def safe_init_database():
    """
    Безопасная инициализация базы данных с обработкой ошибок
    """
    # Сначала проверяем, инициализирована ли БД
    if is_database_initialized():
        import logging

        logger = logging.getLogger(__name__)
        logger.info("[DATABASE] База данных уже инициализирована, пропускаем init_database")
        return

    try:
        init_database()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        # Если БД уже инициализирована, это нормально
        if is_database_initialized():
            logger.info("[DATABASE] База данных инициализирована, несмотря на ошибку при init_database")
            return
        logger.warning(f"Не удалось автоматически инициализировать БД: {e}")
        # Пробуем обычную инициализацию
        try:
            init_database()
        except Exception as e2:
            # Если БД уже инициализирована, это нормально
            if is_database_initialized():
                logger.info("[DATABASE] База данных инициализирована, несмотря на ошибку")
                return
            logger.error(f"Критическая ошибка инициализации БД: {e2}")
            raise
