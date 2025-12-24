"""
Управление соединениями с базой данных
"""

import os
import sqlite3
import time

# Определяем путь к базе данных
_DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_DB_DIR, "osagaming_crm.db")
_DB_PATH = os.path.normpath(_DB_PATH)


def get_db_connection():
    """Return a fresh sqlite3 connection.

    This function intentionally returns a new connection on each call to avoid
    sharing a single sqlite connection object across threads. Callers are
    responsible for closing the connection or using it as a context manager.
    """
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        if "unable to open database file" in error_msg:
            raise RuntimeError(
                f"Cannot open database file: {_DB_PATH}\n"
                f"Directory: {os.path.dirname(_DB_PATH)}\n"
                f"Please check permissions"
            ) from e
        raise


def execute_with_retry(query_func, max_retries=3, retry_delay=0.1):
    """
    Выполнить запрос с повторными попытками при ошибках

    Args:
        query_func: Функция, выполняющая запрос
        max_retries: Максимальное количество попыток
        retry_delay: Задержка между попытками (секунды)

    Returns:
        Результат выполнения query_func
    """
    for attempt in range(max_retries):
        try:
            return query_func()
        except (sqlite3.OperationalError, RuntimeError) as e:
            error_msg = str(e).lower()
            if ("disk i/o error" in error_msg or "i/o error" in error_msg) and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise

    raise RuntimeError(f"Failed to execute query after {max_retries} retries")
