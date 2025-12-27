"""
API эндпоинты для синхронизации с Авито
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ...core.database import get_db, SessionLocal
from ...core.security import get_current_user, is_admin, is_manager
from ...models import User
from ...services.avito_api import AvitoAPI
from ...services.message_sync_service import MessageSyncService
from ...services.chat_pool_service import ChatPoolService

logger = logging.getLogger(__name__)

router = APIRouter()

# Инициализируем сервисы (в реальном приложении это должно быть через dependency injection)
def get_avito_api():
    """Получение экземпляра API Авито"""
    # Здесь должны быть реальные учетные данные
    return AvitoAPI(
        client_id="your_client_id",
        client_secret="your_client_secret"
    )

def get_message_sync_service(avito_api: AvitoAPI = Depends(get_avito_api)):
    """Получение сервиса синхронизации сообщений"""
    return MessageSyncService(avito_api)

@router.post("/sync/start")
async def start_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Запуск синхронизации с Авито"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # Запускаем синхронизацию в фоне
    background_tasks.add_task(
        MessageSyncService(get_avito_api()).start_sync,
        SessionLocal
    )
    
    return {"message": "Синхронизация запущена"}

@router.post("/sync/stop")
async def stop_sync(
    current_user: User = Depends(get_current_user),
):
    """Остановка синхронизации с Авито"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # В реальном приложении нужно хранить ссылку на сервис синхронизации
    # MessageSyncService(get_avito_api()).stop_sync()
    
    return {"message": "Синхронизация остановлена"}

@router.post("/sync/chat/{chat_id}")
async def sync_single_chat(
    chat_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Синхронизация одного чата"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        avito_api = get_avito_api()
        sync_service = MessageSyncService(avito_api)
        
        # Получаем чат из БД
        from ...models import Chat
        chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        
        if not chat:
            # Создаем чат, если его нет
            user_info = avito_api.get_user_info(user_id)
            user_name = user_info.get("name", f"User_{user_id}")
            
            chat = Chat(
                chat_id=chat_id,
                user_id=user_id,
                user_name=user_name,
                status="active",
                last_activity_at=datetime.utcnow()
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
        
        # Синхронизируем сообщения
        await sync_service.sync_single_chat(user_id, {"id": chat_id}, db)
        
        return {"message": "Чат синхронизирован"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации чата: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка синхронизации: {str(e)}"
        )
    finally:
        db.close()

@router.post("/send-message")
async def send_message_to_avito(
    message_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Отправка сообщения в Авито"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    chat_id = message_data.get("chat_id")
    user_id = message_data.get("user_id")
    content = message_data.get("content")
    
    if not all([chat_id, user_id, content]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимы параметры: chat_id, user_id, content"
        )
    
    db = SessionLocal()
    try:
        avito_api = get_avito_api()
        sync_service = MessageSyncService(avito_api)
        
        result = await sync_service.send_message_to_avito(chat_id, user_id, content, db)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка отправки: {str(e)}"
        )
    finally:
        db.close()

@router.get("/chats/{user_id}")
async def get_user_chats(
    user_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Получение списка чатов пользователя"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        avito_api = get_avito_api()
        chats = avito_api.get_user_chats(user_id, limit, offset)
        
        # Обогащаем данными из локальной БД
        from ...models import Chat
        for chat in chats:
            local_chat = db.query(Chat).filter(Chat.chat_id == chat.get("id")).first()
            if local_chat:
                chat["local_status"] = local_chat.status.value if local_chat.status else None
                chat["assigned_manager"] = local_chat.assigned_manager_id
                chat["is_in_pool"] = local_chat.is_in_pool
        
        return {"chats": chats}
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения чатов: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения чатов: {str(e)}"
        )
    finally:
        db.close()

@router.get("/messages/{user_id}/{chat_id}")
async def get_chat_messages(
    user_id: str,
    chat_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """Получение сообщений чата"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    try:
        avito_api = get_avito_api()
        messages = avito_api.get_chat_messages(user_id, chat_id, limit, offset)
        
        return {"messages": messages}
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения сообщений: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения сообщений: {str(e)}"
        )

@router.get("/user/{user_id}")
async def get_user_info(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Получение информации о пользователе"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    try:
        avito_api = get_avito_api()
        user_info = avito_api.get_user_info(user_id)
        
        return user_info
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации: {str(e)}"
        )

@router.post("/extract-urls")
async def extract_avito_urls(
    text_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Извлечение URL Авито из текста"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    text = text_data.get("text", "")
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текст обязателен для анализа"
        )
    
    urls = AvitoAPI.extract_avito_urls(text) if hasattr(AvitoAPI, 'extract_avito_urls') else []
    
    return {"urls": urls}

@router.post("/extract-listing-id")
async def extract_listing_id(
    url_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Извлечение ID объявления из URL"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    url = url_data.get("url", "")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL обязателен для анализа"
        )
    
    listing_id = AvitoAPI.extract_listing_id_from_url(url) if hasattr(AvitoAPI, 'extract_listing_id_from_url') else None
    
    return {"listing_id": listing_id}

@router.get("/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
):
    """Получение статуса синхронизации"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # В реальном приложении здесь должна быть информация о состоянии синхронизации
    return {
        "is_running": False,  # Нужно хранить состояние в переменной или БД
        "last_sync": None,
        "total_chats": 0,
        "total_messages": 0
    }