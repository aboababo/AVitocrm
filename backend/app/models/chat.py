"""
Модель чата
Современная модель для работы с чатами с интеграцией Авито
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    ForeignKey, Enum, Index, func, JSON, Float
)
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.core.database import Base


class ChatStatus(PyEnum):
    """Статусы чата"""
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
    BLOCKED = "blocked"  # Добавлено для совместимости с Avitocrm
    COMPLETED = "completed"  # Добавлено для совместимости с Avitocrm


class ChatPriority(PyEnum):
    """Приоритеты чата"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Chat(Base):
    """Модель чата"""
    
    __tablename__ = "chats"
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shop_id = Column(Integer, ForeignKey("avito_shops.id", ondelete="CASCADE"), nullable=True)  # Магазин Авито
    
    # Внешние идентификаторы (совместимость с Avitocrm)
    chat_id = Column(String(255), unique=True, nullable=True, comment="ID чата в Авито")
    external_id = Column(String(255), unique=True, nullable=True, comment="ID чата во внешней системе")
    customer_id = Column(String(100), nullable=True, comment="ID клиента в Авито")
    
    # Информация о клиенте
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20), nullable=True)
    client_email = Column(String(255), nullable=True)
    client_location = Column(String(200), nullable=True)
    
    # Информация об объявлении (ключевая функция из Avitocrm!)
    product_url = Column(String(500), nullable=True, comment="URL объявления")
    listing_id = Column(String(100), nullable=True, comment="ID объявления")
    listing_data = Column(Text, nullable=True, comment="Полные данные объявления (JSON as text)")
    
    # Статус и приоритет
    status = Column(Enum(ChatStatus), default=ChatStatus.ACTIVE, nullable=False)
    priority = Column(Enum(ChatPriority), default=ChatPriority.NORMAL, nullable=False)
    
    # Метаданные чата
    title = Column(String(200), nullable=True)  # Заголовок чата
    description = Column(Text, nullable=True)   # Описание
    tags = Column(String(500), nullable=True)   # Теги (JSON строка)
    
    # Статистика и таймеры
    message_count = Column(Integer, default=0, nullable=False)
    unread_count = Column(Integer, default=0, nullable=False)
    response_timer = Column(Integer, default=0, comment="Время ответа в минутах")
    last_message = Column(Text, nullable=True, comment="Последнее сообщение (для совместимости)")
    last_activity_at = Column(DateTime(timezone=True), nullable=True, comment="Последняя активность")
    
    # Назначение менеджеру (пул чатов)
    assigned_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_manager_name = Column(String(100), nullable=True)
    is_in_pool = Column(Boolean, default=False, comment="В пуле чатов")
    last_assigned_at = Column(DateTime(timezone=True), nullable=True)
    last_released_at = Column(DateTime(timezone=True), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", foreign_keys=[user_id])
    assigned_manager = relationship("User", foreign_keys=[assigned_manager_id])
    shop = relationship("AvitoShop", back_populates="chats")
    
    messages = relationship(
        "Message", 
        back_populates="chat", 
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    # Связь с кэшем объявлений
    listing_cache = relationship("ListingCache", back_populates="chat", uselist=False)
    
    # Связь с доставками
    deliveries = relationship("Delivery", back_populates="chat", cascade="all, delete-orphan")
    
    # Свойства
    @property
    def last_message_text(self) -> Optional[str]:
        """Последнее сообщение в чате"""
        if self.last_message:
            return self.last_message
        if self.messages:
            return self.messages[-1].content
        return None
    
    @property
    def is_unread(self) -> bool:
        """Есть ли непрочитанные сообщения"""
        return self.unread_count > 0
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Продолжительность чата в минутах"""
        if self.closed_at:
            return int((self.closed_at - self.created_at).total_seconds() / 60)
        return None
    
    @property
    def is_urgent(self) -> bool:
        """Срочный ли чат"""
        return self.priority in [ChatPriority.HIGH, ChatPriority.URGENT]
    
    @property
    def is_active(self) -> bool:
        """Активный ли чат"""
        return self.status in [ChatStatus.ACTIVE, ChatStatus.PENDING]
    
    @property
    def client_display_name(self) -> str:
        """Отображаемое имя клиента"""
        if self.client_name:
            return self.client_name
        return f"Клиент #{self.id}"
    
    @property
    def has_listing(self) -> bool:
        """Есть ли связанное объявление"""
        return bool(self.product_url or self.listing_id)
    
    @property
    def is_assigned(self) -> bool:
        """Назначен ли чат менеджеру"""
        return self.assigned_manager_id is not None
    
    # Методы
    def mark_as_read(self, user_id: int):
        """Отметить сообщения как прочитанные"""
        # TODO: Реализовать логику отметки сообщений как прочитанных
        self.unread_count = 0
    
    def close_chat(self):
        """Закрыть чат"""
        self.status = ChatStatus.CLOSED
        self.closed_at = datetime.utcnow()
    
    def archive_chat(self):
        """Архивировать чат"""
        self.status = ChatStatus.ARCHIVED
    
    def reopen_chat(self):
        """Переоткрыть чат"""
        self.status = ChatStatus.ACTIVE
        self.closed_at = None
    
    def block_chat(self):
        """Заблокировать чат"""
        self.status = ChatStatus.BLOCKED
    
    def assign_to_manager(self, manager_id: int, manager_name: str):
        """Назначить чат менеджеру"""
        self.assigned_manager_id = manager_id
        self.assigned_manager_name = manager_name
        self.is_in_pool = False
        self.last_assigned_at = datetime.utcnow()
    
    def release_to_pool(self):
        """Вернуть чат в пул"""
        self.assigned_manager_id = None
        self.assigned_manager_name = None
        self.is_in_pool = True
        self.last_released_at = datetime.utcnow()
    
    def update_activity(self):
        """Обновить время последней активности"""
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_listing_info(self, product_url: str = None, listing_id: str = None):
        """Обновить информацию об объявлении"""
        if product_url:
            self.product_url = product_url
        if listing_id:
            self.listing_id = listing_id
    
    def __repr__(self) -> str:
        return f"<Chat(id={self.id}, client='{self.client_name}', status='{self.status.value}', has_listing={self.has_listing})>"


class Message(Base):
    """Модель сообщения"""
    
    __tablename__ = "messages"
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    external_id = Column(String(255), unique=True, nullable=True, comment="ID сообщения во внешней системе")
    
    # Контент сообщения
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text", nullable=False)  # text, image, file, etc.
    
    # Статус сообщения (совместимость с Avitocrm)
    is_system = Column(Boolean, default=False, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    message_status = Column(String(20), default="sent", nullable=False)  # sent/delivered/read
    
    # Тип отправителя (совместимость с Avitocrm)
    sender_type = Column(String(20), default="user", nullable=False)  # user/manager/system
    sender_name = Column(String(100), nullable=True)
    
    # Вложения
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(200), nullable=True)
    attachment_size = Column(Integer, nullable=True)
    
    # Метаданные
    extra_data = Column(JSON, nullable=True, comment="Дополнительные данные в JSON")
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True, comment="Временная метка для синхронизации")
    
    # Связи
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")
    
    # Свойства
    @property
    def is_from_user(self) -> bool:
        """Сообщение от пользователя системы"""
        return self.user_id is not None
    
    @property
    def is_from_client(self) -> bool:
        """Сообщение от клиента"""
        return self.user_id is None
    
    @property
    def is_from_manager(self) -> bool:
        """Сообщение от менеджера"""
        return self.sender_type == "manager"
    
    @property
    def has_attachment(self) -> bool:
        """Есть ли вложение"""
        return self.attachment_url is not None
    
    @property
    def sender_display_name(self) -> str:
        """Отображаемое имя отправителя"""
        if self.user:
            return self.user.full_name
        return self.sender_name or "Неизвестно"
    
    # Методы
    def mark_as_read(self):
        """Отметить как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            self.message_status = "read"
    
    def add_attachment(self, url: str, name: str, size: int = None):
        """Добавить вложение"""
        self.attachment_url = url
        self.attachment_name = name
        self.attachment_size = size
        self.message_type = "file"
    
    def set_sender_info(self, sender_type: str, sender_name: str = None):
        """Установить информацию об отправителе"""
        self.sender_type = sender_type
        if sender_name:
            self.sender_name = sender_name
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, chat_id={self.chat_id}, type='{self.message_type}', sender='{self.sender_display_name}')>"


# Добавляем модель для магазинов Авито
class AvitoShop(Base):
    """Модель магазина Авито"""
    
    __tablename__ = "avito_shops"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    shop_url = Column(String(500), unique=True, nullable=False)
    
    # API credentials (совместимость с Avitocrm)
    client_id = Column(String(255), nullable=True)
    client_secret = Column(String(255), nullable=True)
    user_id = Column(String(100), nullable=True, comment="User ID в Авито")
    
    # Статус и настройки
    is_active = Column(Boolean, default=True, nullable=False)
    webhook_registered = Column(Boolean, default=False, nullable=False)
    token_checked_at = Column(DateTime(timezone=True), nullable=True)
    token_status = Column(String(20), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    chats = relationship("Chat", back_populates="shop")
    
    def __repr__(self):
        return f"<AvitoShop(id={self.id}, name='{self.name}')>"


# Индексы для производительности
Index('idx_chats_user_id', Chat.user_id)
Index('idx_chats_status', Chat.status)
Index('idx_chats_priority', Chat.priority)
Index('idx_chats_created_at', Chat.created_at)
Index('idx_chats_last_message_at', Chat.last_message)
Index('idx_chats_assigned_manager_id', Chat.assigned_manager_id)
Index('idx_chats_is_in_pool', Chat.is_in_pool)
Index('idx_chats_shop_id', Chat.shop_id)
Index('idx_chats_product_url', Chat.product_url)

Index('idx_messages_chat_id', Message.chat_id)
Index('idx_messages_user_id', Message.user_id)
Index('idx_messages_created_at', Message.created_at)
Index('idx_messages_is_read', Message.is_read)
Index('idx_messages_timestamp', Message.timestamp)

Index('idx_avito_shops_client_id', AvitoShop.client_id)
Index('idx_avito_shops_user_id', AvitoShop.user_id)