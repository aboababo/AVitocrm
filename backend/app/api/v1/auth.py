"""
Маршруты аутентификации и управления пользователями
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import security_manager
from app.core.config_simple import settings
from app.models.user import User, UserStatus
from app.schemas.user import (
    UserLogin, UserLoginResponse, UserCreate, UserResponse,
    UserPasswordUpdate, CurrentUserUpdate
)
from app.core.security import get_current_active_user


router = APIRouter()


@router.post("/login", response_model=UserLoginResponse)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Вход в систему
    
    Примечание: Для SQLite используем синхронную сессию чтобы избежать
    проблем с aiosqlite и greenlet
    """
    
    # Для SQLite используем синхронную сессию для обхода проблем с асинхронностью
    # SQLite и aiosqlite имеют известные проблемы с greenlet в FastAPI
    sync_session = SessionLocal()
    
    try:
        # Поиск пользователя
        user = sync_session.query(User).filter(User.email == user_credentials.email).first()
        
        if not user:
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        # Проверка пароля
        if not security_manager.verify_password(user_credentials.password, user.hashed_password):
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        # Проверка активности
        if not user.is_active:
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Пользователь неактивен"
            )
        
        # Обновление времени последнего входа
        user.last_login = datetime.utcnow()
        sync_session.commit()
        
        # Создание JWT токена
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security_manager.create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
    
        # Создаем объект схемы UserResponse из модели
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            bio=user.bio,
            status=user.status,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            is_active=user.is_active,
            email_notifications=user.email_notifications,
            push_notifications=user.push_notifications,
            kpi_score=user.kpi_score,
            salary=user.salary,
            temp_password=user.temp_password,
            password_changed=user.password_changed,
            full_name=user.full_name
        )
    
        sync_session.close()
        
        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response
        )
    
    except Exception as e:
        sync_session.close()
        # Перебрасываем HTTPException
        if isinstance(e, HTTPException):
            raise e
        # Логируем другие ошибки
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при аутентификации"
        )
    

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Регистрация нового пользователя
    """
    
    # Для SQLite используем синхронную сессию
    sync_session = SessionLocal()
    
    try:
        # Проверка уникальности email
        existing_user = sync_session.query(User).filter(User.email == user_data.email).first()
        
        if existing_user:
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
        
        # Создание нового пользователя
        hashed_password = security_manager.get_password_hash(user_data.password)
        
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            bio=user_data.bio,
            is_active=user_data.is_active,
            email_notifications=user_data.email_notifications,
            push_notifications=user_data.push_notifications,
            status=UserStatus.ACTIVE
        )
    
        sync_session.add(new_user)
        sync_session.commit()
        sync_session.refresh(new_user)
        
        user_response = UserResponse(
            id=new_user.id,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            phone=new_user.phone,
            bio=new_user.bio,
            status=new_user.status,
            is_superuser=new_user.is_superuser,
            is_verified=new_user.is_verified,
            avatar_url=new_user.avatar_url,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
            last_login=new_user.last_login,
            is_active=new_user.is_active,
            email_notifications=new_user.email_notifications,
            push_notifications=new_user.push_notifications,
            kpi_score=new_user.kpi_score,
            salary=new_user.salary,
            temp_password=new_user.temp_password,
            password_changed=new_user.password_changed,
            full_name=new_user.full_name
        )
        
        sync_session.close()
        return user_response
        
    except Exception as e:
        sync_session.close()
        if isinstance(e, HTTPException):
            raise e
        print(f"Register error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при регистрации"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Получение информации о текущем пользователе
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        bio=current_user.bio,
        status=current_user.status,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        is_active=current_user.is_active,
        email_notifications=current_user.email_notifications,
        push_notifications=current_user.push_notifications,
        kpi_score=current_user.kpi_score,
        salary=current_user.salary,
        temp_password=current_user.temp_password,
        password_changed=current_user.password_changed,
        full_name=current_user.full_name
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: CurrentUserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Обновление профиля текущего пользователя
    """
    
    # Для SQLite используем синхронную сессию
    sync_session = SessionLocal()
    
    try:
        # Находим пользователя в синхронной сессии
        user_to_update = sync_session.query(User).filter(User.id == current_user.id).first()
        
        if not user_to_update:
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Обновление полей
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(user_to_update, field):
                setattr(user_to_update, field, value)
        
        sync_session.commit()
        sync_session.refresh(user_to_update)
        
        user_response = UserResponse(
            id=user_to_update.id,
            email=user_to_update.email,
            first_name=user_to_update.first_name,
            last_name=user_to_update.last_name,
            phone=user_to_update.phone,
            bio=user_to_update.bio,
            status=user_to_update.status,
            is_superuser=user_to_update.is_superuser,
            is_verified=user_to_update.is_verified,
            avatar_url=user_to_update.avatar_url,
            created_at=user_to_update.created_at,
            updated_at=user_to_update.updated_at,
            last_login=user_to_update.last_login,
            is_active=user_to_update.is_active,
            email_notifications=user_to_update.email_notifications,
            push_notifications=user_to_update.push_notifications,
            kpi_score=user_to_update.kpi_score,
            salary=user_to_update.salary,
            temp_password=user_to_update.temp_password,
            password_changed=user_to_update.password_changed,
            full_name=user_to_update.full_name
        )
        
        sync_session.close()
        return user_response
        
    except Exception as e:
        sync_session.close()
        if isinstance(e, HTTPException):
            raise e
        print(f"Update user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при обновлении профиля"
        )


@router.post("/me/change-password")
async def change_password(
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Смена пароля текущего пользователя
    """
    
    # Для SQLite используем синхронную сессию
    sync_session = SessionLocal()
    
    try:
        # Находим пользователя в синхронной сессии
        user_to_update = sync_session.query(User).filter(User.id == current_user.id).first()
        
        if not user_to_update:
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Проверка текущего пароля
        if not security_manager.verify_password(password_data.current_password, user_to_update.hashed_password):
            sync_session.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный текущий пароль"
            )
        
        # Обновление пароля
        new_hashed_password = security_manager.get_password_hash(password_data.new_password)
        user_to_update.hashed_password = new_hashed_password
        
        sync_session.commit()
        sync_session.close()
        
        return {"message": "Пароль успешно изменен"}
        
    except Exception as e:
        sync_session.close()
        if isinstance(e, HTTPException):
            raise e
        print(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при смене пароля"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Выход из системы
    
    В JWT stateless архитектуре клиент должен просто удалить токен
    """
    return {"message": "Успешный выход из системы"}


@router.get("/verify-token")
async def verify_token(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Проверка валидности токена
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name
    }