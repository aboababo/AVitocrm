"""
Тесты для схем валидации
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marshmallow import ValidationError
from utils.schemas import (
    LoginSchema,
    MessageSendSchema,
    ShopCreateSchema,
    UserCreateSchema,
)


def test_user_create_schema_valid():
    """Тест валидных данных для создания пользователя"""
    schema = UserCreateSchema()
    data = {
        "email": "test@example.com",
        "password": "password123",
        "username": "testuser",
        "role": "manager",
    }
    result = schema.load(data)
    assert result["email"] == "test@example.com"
    assert result["username"] == "testuser"


def test_user_create_schema_invalid_email():
    """Тест невалидного email"""
    schema = UserCreateSchema()
    data = {"email": "invalid-email", "password": "password123", "username": "testuser"}
    with pytest.raises(ValidationError):
        schema.load(data)


def test_user_create_schema_short_password():
    """Тест короткого пароля"""
    schema = UserCreateSchema()
    data = {
        "email": "test@example.com",
        "password": "short",  # Меньше 8 символов
        "username": "testuser",
    }
    with pytest.raises(ValidationError):
        schema.load(data)


def test_login_schema_valid():
    """Тест валидных данных для входа"""
    schema = LoginSchema()
    data = {"email": "test@example.com", "password": "password123"}
    result = schema.load(data)
    assert result["email"] == "test@example.com"
    assert result["password"] == "password123"


def test_message_send_schema_valid():
    """Тест валидных данных для отправки сообщения"""
    schema = MessageSendSchema()
    data = {"text": "Hello, world!", "chat_id": 1}
    result = schema.load(data)
    assert result["text"] == "Hello, world!"
    assert result["chat_id"] == 1


def test_message_send_schema_long_text():
    """Тест слишком длинного текста сообщения"""
    schema = MessageSendSchema()
    data = {"text": "x" * 6000, "chat_id": 1}  # Больше 5000 символов
    with pytest.raises(ValidationError):
        schema.load(data)


def test_shop_create_schema_valid():
    """Тест валидных данных для создания магазина"""
    schema = ShopCreateSchema()
    data = {
        "name": "Test Shop",
        "avito_user_id": "user123",
        "client_id": "client123",
        "client_secret": "secret123",
    }
    result = schema.load(data)
    assert result["name"] == "Test Shop"
