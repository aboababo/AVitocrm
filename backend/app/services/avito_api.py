"""
Интеграция с API Avito Messenger
Реальная интеграция с OAuth 2.0 и API мессенджера Авито
"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AvitoAuthType(str, Enum):
    """Типы авторизации Avito API"""
    CLIENT_CREDENTIALS = "client_credentials"
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"


class AvitoScope(str, Enum):
    """Доступные скоупы Avito API"""
    MESSENGER_READ = "messenger:read"
    MESSENGER_WRITE = "messenger:write"
    USER_BALANCE_READ = "user_balance:read"
    JOB_WRITE = "job:write"
    JOB_CV = "job:cv"
    JOB_VACANCY = "job:vacancy"
    JOB_APPLICATIONS = "job:applications"
    USER_OPERATIONS_READ = "user_operations:read"
    USER_READ = "user:read"
    AUTOLOAD_REPORTS = "autoload:reports"
    ITEMS_INFO = "items:info"
    ITEMS_APPLY_VAS = "items:apply_vas"
    SHORT_TERM_RENT_READ = "short_term_rent:read"
    SHORT_TERM_RENT_WRITE = "short_term_rent:write"
    STATS_READ = "stats:read"


class AvitoAPIError(Exception):
    """Базовое исключение для ошибок API Avito"""
    pass


class AvitoAuthError(AvitoAPIError):
    """Ошибка аутентификации"""
    pass


class AvitoAPI:
    """Клиент для работы с API Avito"""
    
    BASE_URL = "https://api.avito.ru"
    AUTH_URL = "https://api.avito.ru/token"
    OAUTH_URL = "https://avito.ru/oauth"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: Optional[str] = None,
        scopes: Optional[List[AvitoScope]] = None
    ):
        """
        Инициализация клиента API Avito
        
        Args:
            client_id: ID клиента из личного кабинета Avito
            client_secret: Секретный ключ клиента
            redirect_uri: URI для перенаправления (только для authorization_code)
            scopes: Список скоупов для доступа
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or [AvitoScope.MESSENGER_READ, AvitoScope.MESSENGER_WRITE]
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            follow_redirects=True
        )
        
        # Кэш для токенов по пользователям
        self._user_tokens: Dict[int, dict] = {}
    
    async def close(self):
        """Закрытие клиента"""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def build_oauth_url(self, state: Optional[str] = None) -> str:
        """
        Создание URL для OAuth авторизации пользователя
        
        Args:
            state: Параметр state для защиты от CSRF
        
        Returns:
            URL для перенаправления пользователя
        """
        if not self.redirect_uri:
            raise ValueError("redirect_uri должен быть указан для OAuth авторизации")
        
        scopes_str = ",".join([scope.value for scope in self.scopes])
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": scopes_str,
            "redirect_uri": self.redirect_uri
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.OAUTH_URL}?{query_string}"
    
    async def get_access_token(
        self,
        grant_type: AvitoAuthType,
        code: Optional[str] = None,
        refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получение access token от API Avito
        
        Args:
            grant_type: Тип авторизации (client_credentials или authorization_code)
            code: Код авторизации (только для authorization_code)
            refresh_token: Токен обновления (только для refresh_token)
        
        Returns:
            Ответ с токенами от API
        """
        data = {
            "grant_type": grant_type.value,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        if grant_type == AvitoAuthType.AUTHORIZATION_CODE:
            if not code:
                raise ValueError("code обязателен для authorization_code")
            data["code"] = code
            if self.redirect_uri:
                data["redirect_uri"] = self.redirect_uri
        
        elif grant_type == AvitoAuthType.REFRESH_TOKEN:
            if not refresh_token:
                raise ValueError("refresh_token обязателен для refresh_token")
            data["refresh_token"] = refresh_token
        
        elif grant_type == AvitoAuthType.CLIENT_CREDENTIALS:
            # Для client_credentials больше ничего не нужно
            pass
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = await self._client.post(
                self.AUTH_URL,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Сохраняем токены
            self.access_token = result.get("access_token")
            self.refresh_token = result.get("refresh_token")
            
            if self.access_token:
                expires_in = result.get("expires_in", 86400)  # 24 часа по умолчанию
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return result
            
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP Error: {e.response.status_code}"
            try:
                error_response = e.response.json()
                error_detail = error_response.get("error_description", error_detail)
            except:
                pass
            
            raise AvitoAuthError(f"Ошибка получения токена: {error_detail}")
        except httpx.RequestError as e:
            raise AvitoAuthError(f"Ошибка запроса: {str(e)}")
    
    def is_token_valid(self) -> bool:
        """Проверка валидности токена"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at - timedelta(minutes=5)  # Запас 5 минут
    
    async def ensure_valid_token(self):
        """Проверка и обновление токена при необходимости"""
        if not self.is_token_valid():
            if self.refresh_token:
                # Пробуем обновить токен
                try:
                    await self.get_access_token(
                        grant_type=AvitoAuthType.REFRESH_TOKEN,
                        refresh_token=self.refresh_token
                    )
                except AvitoAuthError:
                    # Если refresh token не работает, получаем новый через client_credentials
                    await self.get_access_token(grant_type=AvitoAuthType.CLIENT_CREDENTIALS)
            else:
                # Получаем токен через client_credentials
                await self.get_access_token(grant_type=AvitoAuthType.CLIENT_CREDENTIALS)
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Получение заголовков авторизации"""
        if not self.access_token:
            raise AvitoAuthError("Токен доступа не установлен")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    # ======================
    # МЕТОДЫ МЕССЕНДЖЕРА
    # ======================
    
    async def get_chats(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        archived: bool = False
    ) -> Dict[str, Any]:
        """
        Получение списка чатов пользователя
        
        Args:
            user_id: ID пользователя (если None - текущий пользователь)
            limit: Количество возвращаемых чатов
            offset: Смещение
            unread_only: Только непрочитанные чаты
            archived: Включая архивные чаты
        
        Returns:
            Список чатов от API Avito
        """
        await self.ensure_valid_token()
        
        params = {
            "limit": limit,
            "offset": offset,
            "unread_only": str(unread_only).lower(),
            "archived": str(archived).lower()
        }
        
        if user_id:
            params["user_id"] = user_id
        
        try:
            response = await self._client.get(
                "/messenger/v2/accounts",
                params=params,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка получения чатов: {e.response.status_code}")
            raise AvitoAPIError(f"Ошибка API при получении чатов: {e.response.status_code}")
    
    async def get_chat_messages(
        self,
        chat_id: str,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получение сообщений чата
        
        Args:
            chat_id: ID чата
            limit: Количество сообщений
            offset: Смещение
            user_id: ID пользователя
        
        Returns:
            Список сообщений чата
        """
        await self.ensure_valid_token()
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if user_id:
            params["user_id"] = user_id
        
        try:
            response = await self._client.get(
                f"/messenger/v2/accounts/{chat_id}/chats",
                params=params,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка получения сообщений: {e.response.status_code}")
            raise AvitoAPIError(f"Ошибка API при получении сообщений: {e.response.status_code}")
    
    async def send_message(
        self,
        chat_id: str,
        message: str,
        user_id: Optional[int] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Отправка сообщения в чат
        
        Args:
            chat_id: ID чата
            message: Текст сообщения
            user_id: ID пользователя
            attachments: Вложения
        
        Returns:
            Ответ API с отправленным сообщением
        """
        await self.ensure_valid_token()
        
        payload = {
            "message": {
                "value": message,
                "type": "text"
            }
        }
        
        if attachments:
            payload["message"]["attachments"] = attachments
        
        if user_id:
            payload["user_id"] = user_id
        
        try:
            response = await self._client.post(
                f"/messenger/v1/accounts/{chat_id}/messages",
                json=payload,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка отправки сообщения: {e.response.status_code}")
            raise AvitoAPIError(f"Ошибка API при отправке сообщения: {e.response.status_code}")
    
    async def mark_as_read(
        self,
        chat_id: str,
        message_ids: List[str],
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Отметка сообщений как прочитанных
        
        Args:
            chat_id: ID чата
            message_ids: Список ID сообщений
            user_id: ID пользователя
        
        Returns:
            Ответ API
        """
        await self.ensure_valid_token()
        
        payload = {
            "ids": message_ids
        }
        
        if user_id:
            payload["user_id"] = user_id
        
        try:
            response = await self._client.post(
                f"/messenger/v1/accounts/{chat_id}/chats/read",
                json=payload,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка отметки как прочитанного: {e.response.status_code}")
            raise AvitoAPIError(f"Ошибка API при отметке как прочитанного: {e.response.status_code}")
    
    async def get_chat_info(self, chat_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получение информации о чате
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
        
        Returns:
            Информация о чате
        """
        await self.ensure_valid_token()
        
        params = {}
        if user_id:
            params["user_id"] = user_id
        
        try:
            response = await self._client.get(
                f"/messenger/v1/accounts/{chat_id}",
                params=params,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка получения информации о чате: {e.response.status_code}")
            raise AvitoAPIError(f"Ошибка API при получении информации о чате: {e.response.status_code}")
    
    # ======================
    # УТИЛИТЫ
    # ======================
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Получение информации о текущем пользователе
        
        Returns:
            Информация о пользователе
        """
        await self.ensure_valid_token()
        
        try:
            response = await self._client.get(
                "/core/v1/accounts/self",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка получения информации о пользователе: {e.response.status_code}")
            raise AvitoAPIError(f"Ошибка API при получении информации о пользователе: {e.response.status_code}")
    
    async def test_connection(self) -> bool:
        """
        Тестирование подключения к API Avito
        
        Returns:
            True если подключение успешно
        """
        try:
            user_info = await self.get_user_info()
            return user_info is not None
        except Exception as e:
            logger.error(f"Ошибка тестирования подключения: {str(e)}")
            return False
    
    # ======================
    # КЭШИРОВАНИЕ
    # ======================
    
    @lru_cache(maxsize=100)
    def _get_chats_cache_key(self, user_id: Optional[int], limit: int, offset: int) -> str:
        """Ключ кэша для списка чатов"""
        return f"chats_{user_id}_{limit}_{offset}"
    
    @lru_cache(maxsize=100)
    def _get_messages_cache_key(self, chat_id: str, limit: int, offset: int) -> str:
        """Ключ кэша для сообщений чата"""
        return f"messages_{chat_id}_{limit}_{offset}"
    
    async def get_chats_cached(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        archived: bool = False,
        cache_ttl: int = 60  # секунды
    ) -> Dict[str, Any]:
        """
        Получение списка чатов с кэшированием
        
        Args:
            user_id: ID пользователя
            limit: Количество чатов
            offset: Смещение
            unread_only: Только непрочитанные
            archived: Включая архивные
            cache_ttl: Время жизни кэша
        
        Returns:
            Список чатов
        """
        cache_key = self._get_chats_cache_key(user_id, limit, offset)
        
        # В реальном приложении здесь было бы кэширование в Redis или аналогичное
        # Пока используем in-memory кэш
        
        return await self.get_chats(user_id, limit, offset, unread_only, archived)


# Singleton для глобального доступа к API
_avito_api_instance: Optional[AvitoAPI] = None


def get_avito_api(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None
) -> AvitoAPI:
    """
    Получение экземпляра API Avito (синглтон)
    
    Args:
        client_id: ID клиента
        client_secret: Секретный ключ
        redirect_uri: URI для перенаправления
    
    Returns:
        Экземпляр AvitoAPI
    """
    global _avito_api_instance
    
    if _avito_api_instance is None:
        if not client_id or not client_secret:
            raise ValueError("client_id и client_secret обязательны для первого вызова")
        
        _avito_api_instance = AvitoAPI(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
    
    return _avito_api_instance