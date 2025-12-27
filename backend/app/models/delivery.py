"""
Модели для работы с доставками
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional

class DeliveryStatus(PyEnum):
    """Статусы доставки"""
    PROCESSING = "processing"  # В обработке
    PREPARING = "preparing"    # Готовится к отправке
    SHIPPED = "shipped"        # Отправлено
    IN_TRANSIT = "in_transit"  # В пути
    OUT_FOR_DELIVERY = "out_for_delivery"  # В доставке
    DELIVERED = "delivered"    # Доставлено
    FAILED = "failed"         # Не удалось доставить
    RETURNED = "returned"     # Возвращено
    CANCELLED = "cancelled"   # Отменено

class Delivery(Base):
    """Модель доставки"""
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    
    # Основная информация
    delivery_status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PROCESSING, nullable=False)
    tracking_number = Column(String(100), nullable=True, comment="Трек-номер доставки")
    carrier = Column(String(100), nullable=True, comment="Служба доставки")
    
    # Адрес доставки
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(50), nullable=True)
    
    # Получатель
    recipient_name = Column(String(200), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    
    # Стоимость доставки
    delivery_cost = Column(Float, nullable=True, comment="Стоимость доставки")
    delivery_weight = Column(Float, nullable=True, comment="Вес посылки (кг)")
    
    # Даты
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    estimated_delivery = Column(DateTime(timezone=True), nullable=True)
    
    # Дополнительная информация
    notes = Column(Text, nullable=True, comment="Заметки менеджера")
    instructions = Column(Text, nullable=True, comment="Инструкции для курьера")
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    chat = relationship("Chat", back_populates="deliveries")
    
    # Свойства
    @property
    def is_delivered(self) -> bool:
        """Доставлено ли"""
        return self.delivery_status == DeliveryStatus.DELIVERED
    
    @property
    def is_shipped(self) -> bool:
        """Отправлено ли"""
        return self.delivery_status in [
            DeliveryStatus.SHIPPED,
            DeliveryStatus.IN_TRANSIT,
            DeliveryStatus.OUT_FOR_DELIVERY,
            DeliveryStatus.DELIVERED
        ]
    
    @property
    def full_address(self) -> str:
        """Полный адрес"""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)
    
    @property
    def days_in_transit(self) -> Optional[int]:
        """Дней в пути"""
        if self.shipped_at and not self.delivered_at:
            return (datetime.utcnow() - self.shipped_at).days
        elif self.shipped_at and self.delivered_at:
            return (self.delivered_at - self.shipped_at).days
        return None
    
    # Методы
    def mark_as_shipped(self, tracking_number: str = None, carrier: str = None):
        """Отметить как отправленное"""
        self.delivery_status = DeliveryStatus.SHIPPED
        self.shipped_at = datetime.utcnow()
        if tracking_number:
            self.tracking_number = tracking_number
        if carrier:
            self.carrier = carrier
    
    def mark_as_delivered(self):
        """Отметить как доставленное"""
        self.delivery_status = DeliveryStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def cancel_delivery(self, reason: str = None):
        """Отменить доставку"""
        self.delivery_status = DeliveryStatus.CANCELLED
        if reason:
            self.notes = f"Отменено: {reason}"
    
    def __repr__(self) -> str:
        return f"<Delivery(id={self.id}, status='{self.delivery_status.value}', tracking='{self.tracking_number}')>"

# Индексы для производительности
Index('idx_deliveries_chat_id', Delivery.chat_id)
Index('idx_deliveries_status', Delivery.delivery_status)
Index('idx_deliveries_tracking', Delivery.tracking_number)
Index('idx_deliveries_created_at', Delivery.created_at)