"""
Безопасность приложения
JWT аутентификация, авторизация и защита
"""

from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config_simple import settings
from app.core.database import get_db
from app.models.user import User

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Схема для Bearer токена
security = HTTPBearer()

class SecurityManager:
    """Менеджер безопасности"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        try:
            import bcrypt as _bcrypt_mod
            if isinstance(plain_password, str):
                b = plain_password.encode('utf-8')
            else:
                b = plain_password
            if len(b) > 72:
                b = b[:72]
            
            if isinstance(hashed_password, str):
                hp = hashed_password.encode('utf-8')
            elif isinstance(hashed_password, bytes):
                hp = hashed_password
            else:
                hp = str(hashed_password).encode('utf-8')

            return _bcrypt_mod.checkpw(b, hp)
        except Exception as exc:
            print('bcrypt.checkpw failed:', exc)
            return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Хеширование пароля"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Создание JWT токена"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Проверка и декодирование токена"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError:
            return None

# Глобальный экземпляр
security_manager = SecurityManager()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Получение текущего пользователя из JWT токена"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Проверка токена
    payload = security_manager.verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    # Извлечение данных пользователя
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    # Поиск пользователя в БД
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Получение активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=400, 
            detail="Пользователь неактивен"
        )
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Получение суперпользователя"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, 
            detail="Недостаточно прав доступа"
        )
    return current_user

def has_role(user: User, role_name: str) -> bool:
    """Проверка наличия роли у пользователя"""
    if user.is_superuser:
        return True
    # Проверяем через связи many-to-many
    if hasattr(user, 'roles') and user.roles:
        return any(role.name == role_name for role in user.roles)
    # Fallback: проверяем через атрибут role, если он есть
    return getattr(user, 'role', None) == role_name

def is_admin(user: User) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user.is_superuser or has_role(user, "admin")

def is_manager(user: User) -> bool:
    """Проверка, является ли пользователь менеджером"""
    return is_admin(user) or has_role(user, "manager")
        
def require_permissions(required_permissions: List[str]):
    """Декоратор для проверки прав доступа"""
    def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = [perm.name for perm in current_user.permissions]
        
        for permission in required_permissions:
            if permission not in user_permissions and not current_user.is_superuser:
                raise HTTPException(
                    status_code=403,
                    detail=f"Недостаточно прав: требуется {permission}"
                )
        return current_user
    
    return permission_checker

def setup_security(app):
    """Настройка безопасности для FastAPI приложения"""
    
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        """Добавление security headers"""
        response = await call_next(request)
        
        # Защита от XSS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS для HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = \
                "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:;"
        )
        
        return response
    
    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        """Простой rate limiting middleware"""
        response = await call_next(request)
        return response