"""
Сервис синхронизации с API Авито
Автоматическая синхронизация сообщений и чатов
"""

import asyncio
import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import json
import re

from .avito_api import AvitoAPI, extract_avito_urls, extract_listing_id_from_url, format_message_for_avito
from ..models import Chat, Message, User, ListingCache, MessageStatus, ChatStatus
from ..core.database import get_db

logger = logging.getLogger(__name__)

class MessageSyncService:
    """Сервис синхронизации сообщений с Авито"""
    
    def __init__(self, avito_api: AvitoAPI):
        self.avito_api = avito_api
        self.sync_interval = 30  # Интервал синхронизации в секундах
        self.message_cache = {}  # Кэш для избежания дубликатов
        self.is_syncing = False
    
    async def start_sync(self, db_session_factory):
        """Запуск фоновой синхронизации"""
        if self.is_syncing:
            logger.warning("⚠️ Синхронизация уже запущена")
            return
        
        self.is_syncing = True
        logger.info("🚀 Запуск синхронизации с Авито")
        
        while self.is_syncing:
            try:
                await self.sync_all_chats(db_session_factory)
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле синхронизации: {e}")
                await asyncio.sleep(60)  # При ошибке ждем дольше
    
    def stop_sync(self):
        """Остановка синхронизации"""
        self.is_syncing = False
        logger.info("⏹️ Синхронизация остановлена")
    
    async def sync_all_chats(self, db_session_factory):
        """Синхронизация всех чатов"""
        try:
            with db_session_factory() as db:
                # Получаем всех пользователей с активными чатами
                active_users = db.query(Chat.user_id).distinct().all()
                
                for user_result in active_users:
                    user_id = user_result[0]
                    await self.sync_user_chats(user_id, db)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации всех чатов: {e}")
    
    async def sync_user_chats(self, user_id: str, db: Session):
        """Синхронизация чатов пользователя"""
        try:
            # Получаем список чатов с Авито
            avito_chats = self.avito_api.get_user_chats(user_id)
            
            if not avito_chats:
                logger.debug(f"ℹ️ Нет чатов для пользователя {user_id}")
                return
            
            for chat_data in avito_chats:
                await self.sync_single_chat(user_id, chat_data, db)
                
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации чатов пользователя {user_id}: {e}")
    
    async def sync_single_chat(self, user_id: str, chat_data: Dict[str, Any], db: Session):
        """Синхронизация одного чата"""
        try:
            chat_id = chat_data.get("id") or chat_data.get("chat_id")
            if not chat_id:
                return
            
            # Получаем или создаем чат в БД
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            
            if not chat:
                # Извлекаем информацию о пользователе
                user_info = self.avito_api.get_user_info(user_id)
                user_name = user_info.get("name", f"User_{user_id}")
                
                # Извлекаем URL объявления из последних сообщений
                listing_url = None
                listing_id = None
                
                recent_messages = self.avito_api.get_chat_messages(user_id, chat_id, limit=5)
                for message in recent_messages:
                    urls = extract_avito_urls(message.get("text", ""))
                    if urls:
                        listing_url = urls[0]
                        listing_id = extract_listing_id_from_url(listing_url)
                        break
                
                chat = Chat(
                    chat_id=chat_id,
                    user_id=user_id,
                    user_name=user_name,
                    listing_url=listing_url,
                    listing_id=listing_id,
                    status=ChatStatus.ACTIVE,
                    last_activity_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                db.add(chat)
            else:
                # Обновляем информацию чата
                chat.last_activity_at = datetime.utcnow()
                if not chat.listing_id:
                    # Пытаемся найти URL объявления
                    recent_messages = self.avito_api.get_chat_messages(user_id, chat_id, limit=5)
                    for message in recent_messages:
                        urls = extract_avito_urls(message.get("text", ""))
                        if urls:
                            chat.listing_url = urls[0]
                            chat.listing_id = extract_listing_id_from_url(urls[0])
                            break
            
            db.commit()
            
            # Синхронизируем сообщения чата
            await self.sync_chat_messages(user_id, chat_id, chat, db)
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации чата {chat_id}: {e}")
            db.rollback()
    
    async def sync_chat_messages(self, user_id: str, chat_id: str, chat: Chat, db: Session):
        """Синхронизация сообщений чата"""
        try:
            # Получаем последнее сообщение из БД
            last_db_message = db.query(Message).filter(
                Message.chat_id == chat_id
            ).order_by(desc(Message.created_at)).first()
            
            # Параметры для запроса
            offset = 0
            limit = 50
            
            while True:
                # Получаем сообщения с Авито
                avito_messages = self.avito_api.get_chat_messages(
                    user_id, chat_id, limit=limit, offset=offset
                )
                
                if not avito_messages:
                    break
                
                new_messages_count = 0
                
                for message_data in avito_messages:
                    # Проверяем, есть ли уже такое сообщение
                    message_id = message_data.get("id") or message_data.get("message_id")
                    if not message_id:
                        continue
                    
                    existing_message = db.query(Message).filter(
                        Message.message_id == str(message_id)
                    ).first()
                    
                    if existing_message:
                        continue  # Сообщение уже существует
                    
                    # Создаем новое сообщение
                    message_text = message_data.get("text", "") or message_data.get("message", "")
                    message_timestamp = message_data.get("timestamp") or message_data.get("created_at")
                    
                    # Парсим временную метку
                    created_at = datetime.utcnow()
                    if message_timestamp:
                        try:
                            if isinstance(message_timestamp, str):
                                created_at = datetime.fromisoformat(message_timestamp.replace("Z", "+00:00"))
                            elif isinstance(message_timestamp, (int, float)):
                                created_at = datetime.fromtimestamp(message_timestamp, tz=timezone.utc)
                        except:
                            pass
                    
                    # Определяем отправителя
                    sender_type = "user"
                    sender_name = chat.user_name
                    
                    if message_data.get("from_me") or message_data.get("is_from_me"):
                        sender_type = "manager"
                        sender_name = "Я"
                    
                    # Извлекаем URL объявления
                    listing_urls = extract_avito_urls(message_text)
                    
                    new_message = Message(
                        message_id=str(message_id),
                        chat_id=chat_id,
                        content=message_text,
                        sender_type=sender_type,
                        sender_name=sender_name,
                        created_at=created_at,
                        status=MessageStatus.SENT
                    )
                    
                    # Если это первое сообщение с URL, обновляем чат
                    if listing_urls and not chat.listing_url:
                        chat.listing_url = listing_urls[0]
                        chat.listing_id = extract_listing_id_from_url(listing_urls[0])
                    
                    db.add(new_message)
                    new_messages_count += 1
                
                db.commit()
                
                # Если не получили полный лимит, значит это последняя порция
                if len(avito_messages) < limit:
                    break
                
                offset += limit
            
            if new_messages_count > 0:
                logger.info(f"✅ Синхронизировано {new_messages_count} новых сообщений в чате {chat_id}")
                # Обновляем время последней активности чата
                chat.last_activity_at = datetime.utcnow()
                db.commit()
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации сообщений: {e}")
            db.rollback()
    
    async def send_message_to_avito(self, chat_id: str, user_id: str, message_text: str, db: Session) -> Dict[str, Any]:
        """Отправка сообщения в Авито"""
        try:
            # Форматируем сообщение
            formatted_message = format_message_for_avito(message_text)
            
            # Отправляем через API
            result = self.avito_api.send_message(user_id, chat_id, formatted_message)
            
            # Сохраняем сообщение в БД
            message = Message(
                message_id=result.get("id", f"temp_{datetime.utcnow().timestamp()}"),
                chat_id=chat_id,
                content=formatted_message,
                sender_type="manager",
                sender_name="Я",
                created_at=datetime.utcnow(),
                status=MessageStatus.SENT
            )
            
            db.add(message)
            
            # Обновляем чат
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            if chat:
                chat.last_activity_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"✅ Сообщение отправлено в чат {chat_id}")
            return {"success": True, "message_id": message.message_id}
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            db.rollback()
            return {"error": str(e)}
    
    async def get_unread_messages_count(self, user_id: str, chat_id: str) -> int:
        """Получение количества непрочитанных сообщений"""
        try:
            # Это упрощенная версия, в реальности нужно использовать WebSocket
            # или polling для получения количества непрочитанных сообщений
            messages = self.avito_api.get_chat_messages(user_id, chat_id, limit=10)
            
            # Подсчитываем сообщения от пользователя
            unread_count = 0
            for message in messages:
                if not message.get("read") and not message.get("from_me"):
                    unread_count += 1
            
            return unread_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения непрочитанных сообщений: {e}")
            return 0
    
    async def cache_listing_info(self, listing_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Кэширование информации об объявлении"""
        try:
            # Проверяем, есть ли уже в кэше
            cached = db.query(ListingCache).filter(
                ListingCache.listing_id == listing_id
            ).first()
            
            if cached and cached.expires_at > datetime.utcnow():
                return {
                    "title": cached.title,
                    "price": cached.price,
                    "description": cached.description,
                    "images": json.loads(cached.images) if cached.images else []
                }
            
            # Получаем информацию с Авито (здесь нужно реализовать реальный API вызов)
            # Это заглушка - в реальности нужно сделать запрос к API Авито для получения информации об объявлении
            listing_info = {
                "title": f"Объявление {listing_id}",
                "price": "Цена не указана",
                "description": "Описание недоступно",
                "images": []
            }
            
            # Сохраняем в кэш
            if cached:
                cached.title = listing_info["title"]
                cached.price = listing_info["price"]
                cached.description = listing_info["description"]
                cached.images = json.dumps(listing_info["images"])
                cached.expires_at = datetime.utcnow() + timedelta(hours=1)
            else:
                cached = ListingCache(
                    listing_id=listing_id,
                    title=listing_info["title"],
                    price=listing_info["price"],
                    description=listing_info["description"],
                    images=json.dumps(listing_info["images"]),
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                db.add(cached)
            
            db.commit()
            
            return listing_info
            
        except Exception as e:
            logger.error(f"❌ Ошибка кэширования информации об объявлении: {e}")
            db.rollback()
            return None