"""
Интеграция с API Авито
Реальная работа с мессенджером Авито
"""

import requests
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class AvitoAPI:
    """Класс для работы с API Авито"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = None
        self.base_url = "https://api.avito.ru"
        
    def get_access_token(self) -> str:
        """Получение токена доступа"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
            
        url = f"{self.base_url}/token/"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 86400)  # 24 часа по умолчанию
            self.token_expires = datetime.now() + timezone.utc + timezone.timedelta(seconds=expires_in)
            
            logger.info("✅ Получен новый токен доступа Авито")
            return self.access_token
            
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка получения токена: {e}")
            raise Exception(f"Не удалось получить токен доступа: {e}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполнение запроса к API"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs, timeout=30)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка API запроса: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Ответ сервера: {e.response.text}")
            raise Exception(f"Ошибка API: {e}")
    
    def get_chat_messages(self, user_id: str, chat_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение сообщений чата"""
        endpoint = f"/messenger/chats/{chat_id}/messages"
        params = {
            "limit": limit,
            "offset": offset,
            "user_id": user_id
        }
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            
            # Обрабатываем разные форматы ответа
            if isinstance(response, dict):
                return response.get("messages", response.get("items", response.get("data", [])))
            elif isinstance(response, list):
                return response
            else:
                logger.warning(f"⚠️ Неожиданный формат ответа: {type(response)}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения сообщений чата {chat_id}: {e}")
            return []
    
    def send_message(self, user_id: str, chat_id: str, message: str) -> Dict[str, Any]:
        """Отправка сообщения в чат"""
        endpoint = f"/messenger/chats/{chat_id}/messages"
        data = {
            "user_id": user_id,
            "message": {
                "text": message
            }
        }
        
        try:
            response = self._make_request("POST", endpoint, json=data)
            logger.info(f"✅ Сообщение отправлено в чат {chat_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            raise
    
    def get_user_chats(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение списка чатов пользователя"""
        endpoint = "/messenger/chats"
        params = {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        }
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            
            if isinstance(response, dict):
                return response.get("chats", response.get("items", response.get("data", [])))
            elif isinstance(response, list):
                return response
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения чатов: {e}")
            return []
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Получение информации о пользователе"""
        endpoint = f"/users/{user_id}"
        
        try:
            return self._make_request("GET", endpoint)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации пользователя: {e}")
            return {}

# Утилиты для работы с API
def extract_avito_urls(text: str) -> List[str]:
    """Извлечение URL Авито из текста"""
    import re
    url_pattern = r"https?://(?:www\.)?avito\.ru/[^\s]+"
    urls = re.findall(url_pattern, text)
    
    # Фильтруем только URL объявлений
    product_urls = []
    for url in urls:
        if "/items/" in url or "/avito/" in url:
            product_urls.append(url)
    
    return product_urls

def extract_listing_id_from_url(url: str) -> Optional[str]:
    """Извлечение ID объявления из URL"""
    import re
    # Паттерны для разных форматов URL Авито
    patterns = [
        r"/items/(\d+)",  # /items/123456
        r"/(\d+)(?:\?|$)",  # /123456 или /123456?param=value
        r"id=(\d+)",  # ?id=123456
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def format_message_for_avito(message: str) -> str:
    """Форматирование сообщения для отправки в Авито"""
    # Убираем лишние пробелы и переносы
    formatted = message.strip()
    
    # Заменяем множественные переносы на один
    import re
    formatted = re.sub(r'\n\s*\n+', '\n\n', formatted)
    
    # Ограничиваем длину (Авито ограничивает сообщения)
    if len(formatted) > 5000:
        formatted = formatted[:4997] + "..."
    
    return formatted