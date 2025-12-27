"""
API эндпоинты для работы с объявлениями
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
import re

from ...core.database import get_db, SessionLocal
from ...core.security import get_current_user, is_admin
from ...models import User, Chat, ListingCache, SystemSetting
from ...services.avito_api import AvitoAPI, extract_avito_urls, extract_listing_id_from_url
from ...services.message_sync_service import MessageSyncService

logger = logging.getLogger(__name__)

router = APIRouter()

# Получение экземпляра API Авито (заглушка)
def get_avito_api():
    return AvitoAPI(
        client_id="your_client_id",
        client_secret="your_client_secret"
    )

@router.get("/cache/{listing_id}")
async def get_listing_cache(
    listing_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получение кэшированных данных объявления"""
    db = SessionLocal()
    try:
        listing_cache = db.query(ListingCache).filter(
            ListingCache.listing_id == listing_id
        ).first()
        
        if not listing_cache:
            return None
        
        return {
            "title": listing_cache.title,
            "price": listing_cache.price,
            "price_info": listing_cache.price_info,
            "description": listing_cache.description,
            "status": listing_cache.status,
            "category": listing_cache.category,
            "category_name": listing_cache.category_name,
            "location": listing_cache.location,
            "address": listing_cache.address,
            "images": listing_cache.images,
            "main_image_url": listing_cache.main_image_url,
            "listing_data": listing_cache.listing_data
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения кэша объявления: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных объявления"
        )
    finally:
        db.close()

@router.post("/extract-from-url")
async def extract_listing_from_url(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Извлечение данных объявления из URL"""
    db = SessionLocal()
    url = data.get("url")
    chat_id = data.get("chat_id")
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL обязателен"
        )
    
    try:
        # Извлекаем ID объявления из URL
        listing_id = extract_listing_id_from_url(url)
        if not listing_id:
            return {"success": False, "message": "Не удалось извлечь ID объявления из URL"}
        
        # Проверяем кэш
        cached = db.query(ListingCache).filter(
            ListingCache.listing_id == listing_id
        ).first()
        
        if cached:
            return {
                "success": True,
                "listing_data": {
                    "title": cached.title,
                    "price": cached.price,
                    "price_info": cached.price_info,
                    "description": cached.description,
                    "status": cached.status,
                    "category": cached.category,
                    "category_name": cached.category_name,
                    "location": cached.location,
                    "address": cached.address,
                    "images": cached.images,
                    "main_image_url": cached.main_image_url,
                    "listing_data": cached.listing_data
                }
            }
        
        # Если нет в кэше, пробуем получить через API Авито
        # В реальной реализации здесь был бы запрос к API Авито
        listing_data = {
            "title": f"Объявление {listing_id}",
            "price": None,
            "description": "Описание недоступно",
            "status": "active",
            "category": "Общее",
            "location": "Не указано",
            "images": [],
            "main_image_url": None,
            "listing_data": {"source": "extracted", "url": url}
        }
        
        # Сохраняем в кэш
        cache_entry = ListingCache(
            listing_id=listing_id,
            chat_id=chat_id or 0,
            title=listing_data["title"],
            price=listing_data["price"],
            description=listing_data["description"],
            status=listing_data["status"],
            category=listing_data["category"],
            category_name=listing_data["category"],
            location=listing_data["location"],
            images=listing_data["images"],
            main_image_url=listing_data["main_image_url"],
            listing_data=listing_data["listing_data"]
        )
        
        db.add(cache_entry)
        
        # Обновляем данные в чате, если указан chat_id
        if chat_id:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.listing_id = listing_id
                chat.product_url = url
        
        db.commit()
        
        return {
            "success": True,
            "listing_data": listing_data
        }
        
    except Exception as e:
        logger.error(f"Ошибка извлечения объявления: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка извлечения данных объявления"
        )
    finally:
        db.close()

@router.post("/extract-from-chat/{chat_id}")
async def extract_listing_from_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user)
):
    """Извлечение URL объявления из сообщений чата"""
    db = SessionLocal()
    try:
        # Получаем чат
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чат не найден"
            )
        
        # Ищем URL в сообщениях чата
        messages = chat.messages
        found_urls = []
        
        for message in messages:
            urls = extract_avito_urls(message.content)
            found_urls.extend(urls)
        
        if not found_urls:
            return {"success": False, "message": "URL объявления не найден в сообщениях"}
        
        # Берем первый найденный URL
        product_url = found_urls[0]
        listing_id = extract_listing_id_from_url(product_url)
        
        if not listing_id:
            return {"success": False, "message": "Не удалось извлечь ID объявления"}
        
        # Обновляем данные чата
        chat.product_url = product_url
        chat.listing_id = listing_id
        chat.update_activity()
        
        db.commit()
        
        return {
            "success": True,
            "product_url": product_url,
            "listing_id": listing_id
        }
        
    except Exception as e:
        logger.error(f"Ошибка извлечения URL из чата: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка извлечения URL"
        )
    finally:
        db.close()

@router.get("/chat/{chat_id}")
async def get_chat_listing(
    chat_id: int,
    current_user: User = Depends(get_current_user)
):
    """Получение данных объявления для чата"""
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чат не найден"
            )
        
        if not chat.listing_id:
            return {"has_listing": False}
        
        # Получаем кэш объявления
        listing_cache = db.query(ListingCache).filter(
            ListingCache.listing_id == chat.listing_id
        ).first()
        
        if not listing_cache:
            return {"has_listing": False}
        
        return {
            "has_listing": True,
            "listing_id": chat.listing_id,
            "product_url": chat.product_url,
            "listing_data": {
                "title": listing_cache.title,
                "price": listing_cache.price,
                "price_info": listing_cache.price_info,
                "description": listing_cache.description,
                "status": listing_cache.status,
                "category": listing_cache.category,
                "category_name": listing_cache.category_name,
                "location": listing_cache.location,
                "address": listing_cache.address,
                "images": listing_cache.images,
                "main_image_url": listing_cache.main_image_url,
                "listing_data": listing_cache.listing_data
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения объявления чата: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных объявления"
        )
    finally:
        db.close()

@router.post("/bulk-extract")
async def bulk_extract_listings(
    current_user: User = Depends(get_current_user)
):
    """Массовое извлечение URL объявлений из всех чатов"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        # Получаем все чаты без URL объявлений
        chats_without_listings = db.query(Chat).filter(
            Chat.product_url.is_(None),
            Chat.listing_id.is_(None)
        ).all()
        
        extracted_count = 0
        errors = []
        
        for chat in chats_without_listings:
            try:
                # Ищем URL в сообщениях
                messages = chat.messages
                found_urls = []
                
                for message in messages:
                    urls = extract_avito_urls(message.content)
                    found_urls.extend(urls)
                
                if found_urls:
                    product_url = found_urls[0]
                    listing_id = extract_listing_id_from_url(product_url)
                    
                    if listing_id:
                        chat.product_url = product_url
                        chat.listing_id = listing_id
                        chat.update_activity()
                        extracted_count += 1
                        
                        logger.info(f"Извлечен URL для чата {chat.id}: {product_url}")
                
            except Exception as e:
                errors.append(f"Чат {chat.id}: {str(e)}")
                logger.error(f"Ошибка извлечения URL для чата {chat.id}: {e}")
        
        db.commit()
        
        return {
            "success": True,
            "extracted_count": extracted_count,
            "total_chats": len(chats_without_listings),
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Ошибка массового извлечения: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка массового извлечения"
        )
    finally:
        db.close()

@router.delete("/cache/{listing_id}")
async def delete_listing_cache(
    listing_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление кэша объявления"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        cache_entry = db.query(ListingCache).filter(
            ListingCache.listing_id == listing_id
        ).first()
        
        if not cache_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Кэш объявления не найден"
            )
        
        db.delete(cache_entry)
        db.commit()
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Ошибка удаления кэша: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления кэша"
        )
    finally:
        db.close()

@router.get("/statistics")
async def get_listing_statistics(
    current_user: User = Depends(get_current_user)
):
    """Получение статистики по объявлениям"""
    db = SessionLocal()
    try:
        # Общее количество чатов с объявлениями
        chats_with_listings = db.query(Chat).filter(
            Chat.listing_id.isnot(None)
        ).count()
        
        # Общее количество чатов
        total_chats = db.query(Chat).count()
        
        # Количество уникальных объявлений
        unique_listings = db.query(ListingCache.listing_id).distinct().count()
        
        # Статистика по статусам
        status_stats = db.query(
            ListingCache.status,
            func.count(ListingCache.id).label('count')
        ).group_by(ListingCache.status).all()
        
        return {
            "total_chats": total_chats,
            "chats_with_listings": chats_with_listings,
            "unique_listings": unique_listings,
            "completion_rate": round((chats_with_listings / total_chats * 100), 2) if total_chats > 0 else 0,
            "status_statistics": [
                {"status": stat.status, "count": stat.count}
                for stat in status_stats
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики"
        )
    finally:
        db.close()