"""
Тесты для модуля аутентификации
"""

import os
import sys

# Добавляем путь к backend в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import hash_password, is_old_password_hash, verify_password


def test_hash_password():
    """Тест хеширования пароля"""
    password = "test_password_123"
    hashed = hash_password(password)

    # Хеш не должен быть равен оригинальному паролю
    assert hashed != password

    # Хеш должен быть строкой
    assert isinstance(hashed, str)

    # Хеш должен начинаться с $2b$ (bcrypt)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # Два одинаковых пароля должны давать разные хеши (из-за соли)
    hashed2 = hash_password(password)
    assert hashed != hashed2  # Разные соли


def test_verify_password():
    """Тест проверки пароля"""
    password = "test_password_123"
    hashed = hash_password(password)

    # Правильный пароль
    assert verify_password(password, hashed)

    # Неправильный пароль
    assert not verify_password("wrong_password", hashed)


def test_verify_password_empty():
    """Тест проверки пустого пароля"""
    password = ""
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_is_old_password_hash():
    """Тест определения старого формата хеша"""
    # Старый SHA256 формат (64 символа hex)
    old_hash = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94"
    assert is_old_password_hash(old_hash)

    # Новый bcrypt формат
    new_hash = hash_password("test")
    assert not is_old_password_hash(new_hash)

    # Неправильный формат
    assert not is_old_password_hash("short")
    assert not is_old_password_hash("x" * 65)


def test_password_migration_support():
    """Тест поддержки миграции старых паролей"""
    import hashlib

    # Старый SHA256 хеш
    password = "old_password"
    old_hash = hashlib.sha256(password.encode()).hexdigest()

    # verify_password должен поддерживать старый формат
    assert verify_password(password, old_hash)
    assert not verify_password("wrong", old_hash)
