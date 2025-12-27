"""
Модель пользователя
Современная модель с полной функциональностью
"""

from datetime import datetime
from typing import List
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, 
    Text, ForeignKey, Table, Enum, Index, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# Связь многие-ко-многим между пользователями и ролями
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', Integer, ForeignKey('users.id'))
)

# Ассоциативная таблица ролей <-> разрешений (FK-based)
role_permissions_assoc = Table(
    'role_permissions_assoc',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
)


class UserStatus(enum.Enum):
    """Статусы пользователя"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(Base):
    """Модель пользователя"""
    
    __tablename__ = "users"
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Личная информация
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Статус и настройки
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Аватар и профиль
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Настройки уведомлений
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    
    # KPI и производительность
    kpi_score = Column(Float, default=0.0)  # Текущий KPI балл
    salary = Column(Float, default=0.0)      # Зарплата
    temp_password = Column(String(255), nullable=True)  # Временный пароль
    password_changed = Column(Boolean, default=False)   # Изменил ли пароль
    
    # Связи
    roles = relationship(
        "Role",
        secondary=user_roles,
        primaryjoin="User.id==user_roles.c.user_id",
        secondaryjoin="Role.id==user_roles.c.role_id",
        back_populates="users",
        viewonly=False
    )
    
    # Связи с другими сущностями
    # Примечание: связь с `Chat` оставлена в самом `Chat` через foreign_keys,
    # чтобы избежать неоднозначности при наличии нескольких FK на users.id
    # (user_id, assigned_manager_id). Если нужно, восстановите здесь с явным
    # аргументом `foreign_keys`.
    # chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    assigned_roles = relationship(
        "Role",
        secondary=user_roles,
        primaryjoin="User.id==user_roles.c.user_id",
        secondaryjoin="Role.id==user_roles.c.role_id",
        back_populates="assigned_users",
        viewonly=True
    )
    
    # Новые связи для дополнительного функционала
    kpi_history = relationship("app.models.listing.KPIHistory", back_populates="user", cascade="all, delete-orphan")
    automation_rules = relationship("app.models.listing.AutomationRule", back_populates="creator", cascade="all, delete-orphan")
    activity_logs = relationship("app.models.listing.ActivityLog", back_populates="user", cascade="all, delete-orphan")
    work_schedules = relationship("app.models.listing.WorkSchedule", back_populates="user", cascade="all, delete-orphan")
    penalties = relationship("app.models.listing.Penalty", back_populates="manager", foreign_keys="app.models.listing.Penalty.manager_id", cascade="all, delete-orphan")
    
    # Связи для назначений
    created_assignments = relationship(
        "User",
        secondary=user_roles,
        primaryjoin="User.id==user_roles.c.assigned_by",
        secondaryjoin="User.id==user_roles.c.user_id",
        backref="assigned_by_me",
        viewonly=True,
    )
    
    # Свойства
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def permissions(self) -> List[str]:
        """Список разрешений пользователя"""
        permissions = []
        for role in self.roles:
            permissions.extend([perm.name for perm in role.permissions])
        return list(set(permissions))  # Убираем дубликаты
    
    @property
    def has_permission(self, permission: str) -> bool:
        """Проверка наличия разрешения"""
        return self.is_superuser or permission in self.permissions
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', full_name='{self.full_name}')>"


class Role(Base):
    """Модель роли"""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # Системные роли нельзя удалить
    
    # Связи
    users = relationship(
        "User",
        secondary=user_roles,
        primaryjoin="Role.id==user_roles.c.role_id",
        secondaryjoin="User.id==user_roles.c.user_id",
        back_populates="roles",
        viewonly=False
    )
    assigned_users = relationship(
        "User",
        secondary=user_roles,
        primaryjoin="Role.id==user_roles.c.role_id",
        secondaryjoin="User.id==user_roles.c.user_id",
        back_populates="assigned_roles",
        viewonly=True
    )
    # Связь Role -> Permission через assoc table
    permissions = relationship(
        "Permission",
        secondary=role_permissions_assoc,
        back_populates="roles",
        viewonly=False
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"


class Permission(Base):
    """Модель разрешения"""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    resource = Column(String(50), nullable=False)  # chat, message, user, etc.
    action = Column(String(50), nullable=False)    # create, read, update, delete
    
    # Связи
    # Связь Permission -> Role через assoc table
    roles = relationship(
        "Role",
        secondary=role_permissions_assoc,
        back_populates="permissions",
        viewonly=False
    )
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"


# Индексы для производительности
Index('idx_users_email', User.email)
Index('idx_users_status', User.status)
Index('idx_users_created_at', User.created_at)
Index('idx_user_roles_user_id', user_roles.c.user_id)
Index('idx_user_roles_role_id', user_roles.c.role_id)