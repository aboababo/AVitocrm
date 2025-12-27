"""
Pydantic схемы для чатов
Валидация входных и выходных данных API для чатов
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator, Field
from enum import Enum


class ChatStatusEnum(str, Enum):
    """Статусы чата для API"""
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class ChatPriorityEnum(str, Enum):
    """Приоритеты чата для API"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class MessageTypeEnum(str, Enum):
    """Типы сообщений для API"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class ChatBase(BaseModel):
    """Базовая схема чата"""
    client_name: str = Field(..., min_length=1, max_length=100)
    client_phone: Optional[str] = Field(None, max_length=20)
    client_email: Optional[EmailStr] = None
    client_location: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: ChatPriorityEnum = ChatPriorityEnum.NORMAL
    
    @validator('client_name')
    def validate_client_name(cls, v):
        if not v.strip():
            raise ValueError('Имя клиента не может быть пустым')
        return v.strip()
    
    @validator('client_phone')
    def validate_phone(cls, v):
        if v:
            # Простая валидация российского номера
            import re
            phone_pattern = r'^(\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
            if not re.match(phone_pattern, v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValueError('Неверный формат номера телефона')
        return v


class ChatCreate(ChatBase):
    """Схема для создания чата"""
    tags: Optional[str] = Field(None, description="JSON строка с тегами")


class ChatUpdate(BaseModel):
    """Схема для обновления чата"""
    client_name: Optional[str] = Field(None, min_length=1, max_length=100)
    client_phone: Optional[str] = Field(None, max_length=20)
    client_email: Optional[EmailStr] = None
    client_location: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[ChatPriorityEnum] = None
    status: Optional[ChatStatusEnum] = None
    tags: Optional[str] = None


class ChatResponse(ChatBase):
    """Схема ответа с данными чата"""
    id: int
    user_id: int
    shop_id: Optional[int] = None
    chat_id: Optional[str] = None
    external_id: Optional[str] = Field(None, description="ID чата во внешней системе (например, Avito)")
    customer_id: Optional[str] = None
    product_url: Optional[str] = None
    listing_id: Optional[str] = None
    listing_data: Optional[str] = None
    status: ChatStatusEnum
    message_count: int
    unread_count: int
    response_timer: Optional[int] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    assigned_manager_id: Optional[int] = None
    assigned_manager_name: Optional[str] = None
    is_in_pool: bool = False
    last_assigned_at: Optional[datetime] = None
    last_released_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    
    # Вычисляемые поля
    is_unread: bool
    is_urgent: bool
    duration_minutes: Optional[int]
    client_display_name: str
    
    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Схема списка чатов с пагинацией"""
    chats: List[ChatResponse]
    total: int
    page: int
    size: int
    pages: int


class ChatStatusUpdate(BaseModel):
    """Схема для обновления статуса чата"""
    status: ChatStatusEnum


class ChatFilter(BaseModel):
    """Схема для фильтрации чатов"""
    status: Optional[ChatStatusEnum] = None
    priority: Optional[ChatPriorityEnum] = None
    search: Optional[str] = Field(None, description="Поиск по имени клиента или заголовку")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class MessageBase(BaseModel):
    """Базовая схема сообщения"""
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Содержимое сообщения не может быть пустым')
        return v.strip()


class MessageCreate(MessageBase):
    """Схема для создания сообщения"""
    chat_id: int = Field(..., gt=0)
    # attachment_url: Optional[str] = None  # Будет добавлено в будущем
    # attachment_name: Optional[str] = None
    # attachment_size: Optional[int] = None


class MessageResponse(MessageBase):
    """Схема ответа с данными сообщения"""
    id: int
    chat_id: int
    user_id: Optional[int] = None
    is_system: bool
    is_read: bool
    is_edited: bool
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    read_at: Optional[datetime] = None
    external_id: Optional[str] = Field(None, description="ID сообщения во внешней системе (например, Avito)")
    
    # Вычисляемые поля
    is_from_user: bool
    is_from_client: bool
    has_attachment: bool
    sender_name: str
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Схема списка сообщений"""
    messages: List[MessageResponse]
    total: int
    page: int
    size: int
    pages: int


class MessageReadUpdate(BaseModel):
    """Схема для отметки сообщений как прочитанных"""
    message_ids: List[int] = Field(..., min_items=1)


class ChatStats(BaseModel):
    """Статистика чатов"""
    total_chats: Optional[int] = 0
    active_chats: Optional[int] = 0
    pending_chats: Optional[int] = 0
    closed_chats: Optional[int] = 0
    urgent_chats: Optional[int] = 0
    total_messages: Optional[int] = 0
    unread_messages: Optional[int] = 0
    
    # Средние показатели
    avg_response_time_minutes: Optional[float] = None
    avg_chat_duration_minutes: Optional[float] = None


class QuickReply(BaseModel):
    """Быстрые ответы"""
    id: int
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=1000)
    is_active: bool = True
    
    class Config:
        from_attributes = True