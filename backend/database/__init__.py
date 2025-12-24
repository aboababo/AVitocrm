"""Database package helpers.

This module re-exports low-level helpers from ``database.connection`` and
``database.schema`` and provides a convenience context manager
``get_connection`` which yields a sqlite3 connection and ensures it is
closed on exit.

Public API:
- ``get_db_connection``: low-level factory that returns a fresh
  ``sqlite3.Connection`` (caller must close it).
- ``get_connection``: context manager that yields a connection and closes
  it on exit (preferred for new code).
- ``execute_with_retry`` and ``_DB_PATH`` re-exported from
  ``.connection``.
"""

from contextlib import contextmanager

from .connection import _DB_PATH, execute_with_retry, get_db_connection
from .schema import init_database, is_database_initialized, safe_init_database


@contextmanager
def get_connection():
    """Context manager that yields a sqlite3 connection and closes it on exit.

    Usage:

        with get_connection() as conn:
            conn.execute(...)
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


__all__ = [
    "get_db_connection",
    "get_connection",
    "execute_with_retry",
    "init_database",
    "safe_init_database",
    "is_database_initialized",
    "_DB_PATH",
]
