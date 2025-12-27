"""
Pydantic схемы для пользователей
Валидация входных и выходных данных API
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator, Field
from enum import Enum


class UserStatusEnum(str, Enum):
    """Статусы пользователя для API"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    is_active: bool = True
    email_notifications: bool = True
    push_notifications: bool = True
    
    @validator('first_name')
    def validate_first_name(cls, v):
        if not v.strip():
            raise ValueError('Имя не может быть пустым')
        return v.strip()
    
    @validator('last_name')
    def validate_last_name(cls, v):
        if not v.strip():
            raise ValueError('Фамилия не может быть пустой')
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            # Простая валидация российского номера
            import re
            phone_pattern = r'^(\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
            if not re.match(phone_pattern, v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValueError('Неверный формат номера телефона')
        return v


class UserCreate(UserBase):
    """Схема для создания пользователя"""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        return v


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    """Схема для смены пароля"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        return v


class UserResponse(UserBase):
    """Схема ответа с данными пользователя"""
    id: int
    status: UserStatusEnum
    is_superuser: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    # Вычисляемые поля
    full_name: str
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Схема списка пользователей с пагинацией"""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserLogin(BaseModel):
    """Схема для входа в систему"""
    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    """Ответ при успешном входе"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RoleBase(BaseModel):
    """Базовая схема роли"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class RoleCreate(RoleBase):
    """Схема для создания роли"""
    pass


class RoleResponse(RoleBase):
    """Схема ответа с данными роли"""
    id: int
    is_system: bool
    
    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """Базовая схема разрешения"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)


class PermissionResponse(PermissionBase):
    """Схема ответа с данными разрешения"""
    id: int
    
    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    """Схема для назначения ролей пользователю"""
    role_ids: List[int] = Field(..., min_items=1)


class CurrentUserUpdate(BaseModel):
    """Схема для обновления данных текущего пользователя"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None