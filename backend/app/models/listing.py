"""
Модели для работы с объявлениями и их кэшированием
"""

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ListingCache(Base):
    """Кэш данных объявлений для чатов"""
    __tablename__ = "listing_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(String(50), index=True, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    # Основная информация об объявлении
    title = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    price_info = Column(JSON, nullable=True)  # Дополнительная информация о цене
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)  # active/archived/sold и т.д.
    category = Column(String(100), nullable=True)
    category_name = Column(String(200), nullable=True)
    
    # Местоположение
    location = Column(String(200), nullable=True)
    address = Column(String(300), nullable=True)
    
    # Изображения
    images = Column(JSON, nullable=True)  # JSON массив URL изображений
    main_image_url = Column(String(500), nullable=True)
    
    # Полные данные объявления
    listing_data = Column(JSON, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    chat = relationship("Chat", back_populates="listing_cache")
    
    def __repr__(self):
        return f"<ListingCache(id={self.id}, listing_id='{self.listing_id}', title='{self.title}')>"

class SystemSetting(Base):
    """Системные настройки"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(20), default="string")  # string/number/boolean/json
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemSetting(key='{self.setting_key}', value='{self.setting_value}')>"

class KPISetting(Base):
    """Настройки KPI для менеджеров"""
    __tablename__ = "kpi_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    parameter_name = Column(String(100), unique=True, nullable=False)
    weight = Column(Float, default=1.0)  # Вес параметра
    min_value = Column(Float, default=0)  # Минимальное значение
    penalty_amount = Column(Float, default=0)  # Штраф
    bonus_amount = Column(Float, default=0)  # Бонус
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<KPISetting(parameter='{self.parameter_name}', weight={self.weight})>"

class KPIHistory(Base):
    """История KPI менеджеров"""
    __tablename__ = "kpi_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Период
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # KPI метрики
    response_time_avg = Column(Float, nullable=True)  # Среднее время ответа
    conversion_rate = Column(Float, nullable=True)  # Конверсия
    customer_satisfaction = Column(Float, nullable=True)  # Удовлетворенность клиентов
    messages_per_chat = Column(Float, nullable=True)  # Сообщений на чат
    total_score = Column(Float, nullable=True)  # Общий балл
    
    # Финансовые показатели
    bonus_amount = Column(Float, default=0)
    penalty_amount = Column(Float, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    user = relationship("User", back_populates="kpi_history")
    
    def __repr__(self):
        return f"<KPIHistory(user_id={self.user_id}, period='{self.period_start} - {self.period_end}')>"

class RolePermission(Base):
    """Права доступа для ролей"""
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False, index=True)  # admin/manager
    permission_key = Column(String(100), nullable=False)
    is_allowed = Column(Boolean, default=True)
    
    __table_args__ = (
        {"extend_existing": True},
    )
    
    def __repr__(self):
        return f"<RolePermission(role='{self.role}', permission='{self.permission_key}')>"

class AutomationRule(Base):
    """Правила автоматизации"""
    __tablename__ = "automation_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    
    # Триггер
    trigger_type = Column(String(50), nullable=False)  # new_chat/time_based/keyword
    trigger_condition = Column(JSON, nullable=True)  # JSON с условиями
    
    # Действие
    action_type = Column(String(50), nullable=False)  # auto_reply/assign/priority
    action_data = Column(JSON, nullable=True)  # JSON с данными действия
    
    # Статус
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    creator = relationship("User", back_populates="automation_rules")
    
    def __repr__(self):
        return f"<AutomationRule(name='{self.name}', trigger='{self.trigger_type}')>"

class ActivityLog(Base):
    """Логи активности пользователей"""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(100), nullable=False)  # login/logout/send_message/etc
    action_description = Column(Text, nullable=True)
    target_type = Column(String(50), nullable=True)  # chat/user/shop/etc
    target_id = Column(Integer, nullable=True)
    extra_data = Column(JSON, nullable=True)  # JSON с дополнительными данными
    ip_address = Column(String(45), nullable=True)  # IPv6 поддержка
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    user = relationship("User", back_populates="activity_logs")
    
    def __repr__(self):
        return f"<ActivityLog(user_id={self.user_id}, action='{self.action_type}')>"

class WorkSchedule(Base):
    """График работы менеджеров"""
    __tablename__ = "work_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Понедельник, 1=Вторник, ..., 6=Воскресенье
    start_time = Column(String(8), nullable=False)  # HH:MM формат
    end_time = Column(String(8), nullable=False)    # HH:MM формат
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    user = relationship("User", back_populates="work_schedules")
    
    __table_args__ = (
        {"extend_existing": True},
    )
    
    def __repr__(self):
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        return f"<WorkSchedule(user_id={self.user_id}, day='{days[self.day_of_week]}', time='{self.start_time}-{self.end_time}')>"

class Penalty(Base):
    """Штрафы менеджеров"""
    __tablename__ = "penalties"
    
    id = Column(Integer, primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_id = Column(Integer, nullable=True)
    penalty_type = Column(String(100), nullable=False)  # late_shift/poor_performance/etc
    penalty_amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    is_paid = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # admin who created penalty
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    manager = relationship("User", foreign_keys=[manager_id], back_populates="penalties")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<Penalty(manager_id={self.manager_id}, type='{self.penalty_type}', amount={self.penalty_amount})>"