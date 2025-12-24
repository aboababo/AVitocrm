"""
OSAGAMING CRM - Схемы валидации данных
=======================================

Использует marshmallow для валидации входных данных API
"""

from marshmallow import Schema, fields, validate


class UserCreateSchema(Schema):
    """Схема для создания пользователя"""

    email = fields.Email(
        required=True,
        error_messages={
            "required": "Email обязателен",
            "invalid": "Неверный формат email",
        },
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error="Пароль должен быть минимум 8 символов"),
    )
    username = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100, error="Имя пользователя от 2 до 100 символов"),
    )
    role = fields.Str(validate=validate.OneOf(["manager", "admin"], error="Роль должна быть manager или admin"))
    first_name = fields.Str(allow_none=True, validate=validate.Length(max=100))
    last_name = fields.Str(allow_none=True, validate=validate.Length(max=100))
    salary = fields.Decimal(allow_none=True, validate=validate.Range(min=0))


class UserUpdateSchema(Schema):
    """Схема для обновления пользователя"""

    email = fields.Email(allow_none=True, error_messages={"invalid": "Неверный формат email"})
    username = fields.Str(allow_none=True, validate=validate.Length(min=2, max=100))
    password = fields.Str(allow_none=True, validate=validate.Length(min=8))
    first_name = fields.Str(allow_none=True, validate=validate.Length(max=100))
    last_name = fields.Str(allow_none=True, validate=validate.Length(max=100))
    salary = fields.Decimal(allow_none=True, validate=validate.Range(min=0))
    is_active = fields.Bool(allow_none=True)
    role = fields.Str(allow_none=True, validate=validate.OneOf(["manager", "admin", "super_admin"]))


class ChatUpdateSchema(Schema):
    """Схема для обновления чата"""

    status = fields.Str(
        allow_none=True,
        validate=validate.OneOf(["active", "completed", "archived"], error="Неверный статус"),
    )
    priority = fields.Str(
        allow_none=True,
        validate=validate.OneOf(["low", "normal", "high", "urgent"], error="Неверный приоритет"),
    )
    assigned_manager_id = fields.Int(allow_none=True)


class MessageSendSchema(Schema):
    """Схема для отправки сообщения"""

    text = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=5000, error="Текст сообщения от 1 до 5000 символов"),
    )
    chat_id = fields.Int(required=True, error_messages={"required": "chat_id обязателен"})


class ShopCreateSchema(Schema):
    """Схема для создания магазина"""

    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200, error="Название магазина от 1 до 200 символов"),
    )
    avito_user_id = fields.Str(required=True, error_messages={"required": "avito_user_id обязателен"})
    client_id = fields.Str(required=True, error_messages={"required": "client_id обязателен"})
    client_secret = fields.Str(required=True, error_messages={"required": "client_secret обязателен"})


class ShopUpdateSchema(Schema):
    """Схема для обновления магазина"""

    name = fields.Str(allow_none=True, validate=validate.Length(min=1, max=200))
    client_id = fields.Str(allow_none=True)
    client_secret = fields.Str(allow_none=True)
    is_active = fields.Bool(allow_none=True)


class LoginSchema(Schema):
    """Схема для входа"""

    email = fields.Email(required=True, error_messages={"required": "Email обязателен"})
    password = fields.Str(required=True, error_messages={"required": "Пароль обязателен"})


class PasswordChangeSchema(Schema):
    """Схема для смены пароля"""

    current_password = fields.Str(required=True, error_messages={"required": "Текущий пароль обязателен"})
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error="Новый пароль должен быть минимум 8 символов"),
    )


class PaginationSchema(Schema):
    """Схема для пагинации"""

    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=50, validate=validate.Range(min=1, max=100))
