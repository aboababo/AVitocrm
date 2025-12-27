"""
Схемы для работы с Avito API
Валидация данных для интеграции с Avito Messenger API
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AvitoSyncRequest(BaseModel):
    """Схема для запроса синхронизации с Avito API"""
    
    user_id: Optional[str] = Field(None, description="ID пользователя в Avito (опционально)")
    limit: int = Field(50, ge=1, le=100, description="Количество чатов для синхронизации")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
    include_archived: bool = Field(False, description="Включать ли архивные чаты")
    sync_messages: bool = Field(True, description="Синхронизировать ли сообщения")
    sync_unread_only: bool = Field(False, description="Синхронизировать только непрочитанные сообщения")
    message_limit: int = Field(100, ge=1, le=200, description="Количество сообщений для синхронизации на чат")
    message_offset: int = Field(0, ge=0, description="Смещение для пагинации сообщений")


class AvitoSyncResponse(BaseModel):
    """Схема ответа на запрос синхронизации с Avito API"""
    
    synced_chats: int = Field(..., description="Количество синхронизированных чатов")
    synced_messages: int = Field(..., description="Количество синхронизированных сообщений")
    total_avito_chats: int = Field(..., description="Всего чатов в Avito API")
    has_more: bool = Field(..., description="Есть ли еще данные для синхронизации")


class AvitoChatResponse(BaseModel):
    """Схема ответа с данными чата из Avito API"""
    
    id: str = Field(..., description="ID чата в Avito")
    user_id: str = Field(..., description="ID пользователя Avito")
    item_id: Optional[str] = Field(None, description="ID объявления")
    item_title: Optional[str] = Field(None, description="Название объявления")
    counterpart_name: str = Field(..., description="Имя собеседника")
    counterpart_image: Optional[str] = Field(None, description="Аватар собеседника")
    unread_count: int = Field(default=0, description="Количество непрочитанных сообщений")
    last_message: Optional[str] = Field(None, description="Текст последнего сообщения")
    last_message_time: Optional[datetime] = Field(None, description="Время последнего сообщения")
    is_archived: bool = Field(default=False, description="Архивирован ли чат")
    created_time: datetime = Field(..., description="Время создания чата")
    updated_time: datetime = Field(..., description="Время последнего обновления")
    
    class Config:
        from_attributes = True


class AvitoMessageResponse(BaseModel):
    """Схема ответа с данными сообщения из Avito API"""
    
    id: str = Field(..., description="ID сообщения в Avito")
    chat_id: str = Field(..., description="ID чата")
    author_id: Optional[str] = Field(None, description="ID автора (None для клиента)")
    content: str = Field(..., description="Текст сообщения")
    type: str = Field(default="text", description="Тип сообщения")
    status: str = Field(default="sent", description="Статус сообщения")
    is_read: bool = Field(default=False, description="Прочитано ли сообщение")
    read_time: Optional[datetime] = Field(None, description="Время прочтения")
    created_time: datetime = Field(..., description="Время создания сообщения")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Вложения")
    
    class Config:
        from_attributes = True


class AvitoWebhookRequest(BaseModel):
    """Схема для запроса webhook от Avito"""
    
    type: str = Field(..., description="Тип события (message, chat, etc.)")
    data: Dict[str, Any] = Field(..., description="Данные события")
    timestamp: datetime = Field(..., description="Время события")


class AvitoWebhookRegistration(BaseModel):
    """Схема для регистрации webhook в Avito API"""
    
    webhook_url: str = Field(..., description="URL для получения webhook событий")
    events: List[str] = Field(["message", "chat"], description="Типы событий для подписки")


class AvitoCredentials(BaseModel):
    """Схема для обновления учетных данных Avito API"""
    
    access_token: Optional[str] = Field(None, description="Access token для Avito API")
    client_id: Optional[str] = Field(None, description="Client ID для Avito API")
    client_secret: Optional[str] = Field(None, description="Client Secret для Avito API")
    refresh_token: Optional[str] = Field(None, description="Refresh token для Avito API")


class AvitoAuthResponse(BaseModel):
    """Схема ответа при аутентификации в Avito API"""
    
    success: bool = Field(..., description="Успешность аутентификации")
    access_token: Optional[str] = Field(None, description="Access token")
    expires_in: Optional[int] = Field(None, description="Время жизни токена в секундах")
    token_type: Optional[str] = Field(None, description="Тип токена")
    scope: Optional[str] = Field(None, description="Scope токена")


class AvitoTokenRequest(BaseModel):
    """Схема для запроса токена доступа"""
    
    grant_type: str = Field(default="client_credentials", description="Тип авторизации")
    client_id: Optional[str] = Field(None, description="ID клиента")
    client_secret: Optional[str] = Field(None, description="Секрет клиента")
    code: Optional[str] = Field(None, description="Код авторизации (для authorization_code)")
    refresh_token: Optional[str] = Field(None, description="Токен обновления")


class AvitoTokenResponse(BaseModel):
    """Схема ответа с токеном доступа"""
    
    access_token: str = Field(..., description="Токен доступа")
    expires_in: int = Field(..., description="Время жизни токена в секундах")
    token_type: str = Field(..., description="Тип токена")
    refresh_token: Optional[str] = Field(None, description="Токен обновления")


class AvitoMessageRequest(BaseModel):
    """Схема для отправки сообщения"""
    
    text: str = Field(..., min_length=1, max_length=4000, description="Текст сообщения")


class AvitoRatingResponse(BaseModel):
    """Схема ответа с информацией о рейтинге"""
    
    isEnabled: bool = Field(..., description="Включен ли рейтинг")
    rating: Optional[Dict[str, Any]] = Field(None, description="Информация о рейтинге")


class AvitoReviewResponse(BaseModel):
    """Схема ответа с информацией об отзывах"""
    
    reviews: List[Dict[str, Any]] = Field(..., description="Список отзывов")
    total: int = Field(..., description="Общее количество отзывов")


class AvitoReviewAnswerRequest(BaseModel):
    """Схема для ответа на отзыв"""
    
    review_id: int = Field(..., description="ID отзыва")
    message: str = Field(..., min_length=1, max_length=2000, description="Текст ответа")