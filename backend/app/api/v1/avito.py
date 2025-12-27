"""Avito API роуты
Интеграция с Avito API для работы с мессенджером и отзывами
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import asyncio
import httpx
from datetime import datetime

from app.core.config_simple import settings
from app.services.avito_service import avito_client, AvitoTokenResponse
from app.schemas.avito import (
    AvitoTokenRequest,
    AvitoTokenResponse as AvitoTokenResponseSchema,
    AvitoChatResponse,
    AvitoMessageResponse,
    AvitoMessageRequest,
    AvitoWebhookRequest,
    AvitoRatingResponse,
    AvitoReviewResponse,
    AvitoReviewAnswerRequest
)

router = APIRouter(prefix="/avito", tags=["avito"])


@router.get("/health")
async def avito_health_check():
    """Проверка состояния Avito API"""
    return {
        "status": "healthy",
        "has_credentials": avito_client.has_credentials(),
        "has_token": avito_client.has_token(),
        "environment": settings.ENVIRONMENT
    }


@router.post("/token", response_model=AvitoTokenResponseSchema)
async def get_access_token(request: AvitoTokenRequest):
    """Получение токена доступа к Avito API"""
    
    if not settings.has_avito_keys:
        raise HTTPException(
            status_code=400, 
            detail="Не настроены учетные данные Avito API. Укажите AVITO_ACCESS_TOKEN, AVITO_CLIENT_ID и AVITO_CLIENT_SECRET в переменных окружения."
        )

    try:
        async with avito_client as client:
            await client._refresh_token(request.grant_type)
            
            if client.credentials.expires_at:
                expires_in = int((client.credentials.expires_at - datetime.now()).total_seconds())
            else:
                expires_in = 86400  # 24 часа по умолчанию
            
            return AvitoTokenResponseSchema(
                access_token=client.credentials.access_token,
                expires_in=expires_in,
                token_type="Bearer",
                refresh_token=client.credentials.refresh_token
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения токена: {str(e)}")


@router.get("/chats")
async def get_avito_chats(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    item_ids: Optional[List[int]] = None,
    unread_only: bool = False,
    chat_types: Optional[List[str]] = ["u2i", "u2u"]
):
    """Получение списка чатов через Avito API"""
    
    try:
        async with avito_client as client:
            params = {
                "limit": limit,
                "offset": offset,
                "unread_only": str(unread_only).lower(),
                "chat_types": ",".join(chat_types)
            }
            
            if item_ids:
                params["item_ids"] = ",".join(map(str, item_ids))
            
            result = await client.get_chats(user_id, **params)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения чатов: {str(e)}")


@router.get("/chats/{chat_id}")
async def get_avito_chat_info(user_id: int, chat_id: str):
    """Получение информации по конкретному чату"""
    
    try:
        async with avito_client as client:
            result = await client.get_chat_info(user_id, chat_id)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации о чате: {str(e)}")


@router.get("/chats/{chat_id}/messages")
async def get_avito_messages(
    user_id: int,
    chat_id: str,
    limit: int = 100,
    offset: int = 0
):
    """Получение списка сообщений в чате"""
    
    try:
        async with avito_client as client:
            params = {"limit": limit, "offset": offset}
            result = await client.get_messages(user_id, chat_id, **params)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения сообщений: {str(e)}")


@router.post("/chats/{chat_id}/messages")
async def send_avito_message(
    user_id: int,
    chat_id: str,
    request: AvitoMessageRequest
):
    """Отправка сообщения в чат"""
    
    try:
        async with avito_client as client:
            result = await client.send_message(user_id, chat_id, request.text)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки сообщения: {str(e)}")


@router.post("/chats/{chat_id}/read")
async def mark_avito_chat_as_read(user_id: int, chat_id: str):
    """Отметка чата как прочитанного"""
    
    try:
        async with avito_client as client:
            result = await client.mark_chat_as_read(user_id, chat_id)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отметки чата как прочитанного: {str(e)}")


@router.get("/ratings")
async def get_avito_rating_info():
    """Получение информации о рейтинге"""
    
    try:
        async with avito_client as client:
            result = await client.get_rating_info()
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации о рейтинге: {str(e)}")


@router.get("/reviews")
async def get_avito_reviews(
    offset: int = 0,
    limit: int = 20
):
    """Получение списка отзывов"""
    
    try:
        async with avito_client as client:
            result = await client.get_reviews(offset=offset, limit=limit)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов: {str(e)}")


@router.post("/reviews/answers")
async def add_avito_review_answer(request: AvitoReviewAnswerRequest):
    """Ответ на отзыв"""
    
    try:
        async with avito_client as client:
            result = await client.add_review_answer(request.review_id, request.message)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка добавления ответа на отзыв: {str(e)}")


@router.delete("/reviews/answers/{answer_id}")
async def delete_avito_review_answer(answer_id: int):
    """Удаление ответа на отзыв"""
    
    try:
        async with avito_client as client:
            result = await client.delete_review_answer(answer_id)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления ответа на отзыв: {str(e)}")


@router.post("/webhook")
async def avito_webhook_handler(request: AvitoWebhookRequest, background_tasks: BackgroundTasks):
    """Обработчик webhook уведомлений от Avito"""
    
    background_tasks.add_task(process_avito_webhook, request)
    
    return {"status": "received", "timestamp": datetime.now().isoformat()}


async def process_avito_webhook(request: AvitoWebhookRequest):
    """Фоновая обработка webhook уведомлений"""
    
    try:
        if request.type == "message":
            print(f"Получено уведомление о новом сообщении: {request.data}")
            # Здесь можно добавить логику обработки нового сообщения
            # Например, обновить базу данных, отправить уведомление пользователю и т.д.
        
        elif request.type == "chat":
            print(f"Получено уведомление о чате: {request.data}")
            # Обработка событий чата
        
        else:
            print(f"Неизвестный тип webhook: {request.type}")
    
    except Exception as e:
        print(f"Ошибка обработки webhook: {e}")


@router.get("/subscriptions")
async def get_avito_webhook_subscriptions():
    """Получение списка webhook подписок"""
    
    try:
        async with avito_client as client:
            result = await client.get_webhook_subscriptions()
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения подписок: {str(e)}")


@router.post("/blacklist/{user_id}")
async def add_avito_to_blacklist(user_id: int, blocked_user_ids: List[int]):
    """Добавление пользователей в blacklist"""
    
    try:
        async with avito_client as client:
            result = await client.add_to_blacklist(user_id, blocked_user_ids)
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка добавления в blacklist: {str(e)}")


@router.get("/demo/status")
async def demo_status():
    """Демо-статус для отладки"""
    
    return {
        "demo_mode": not settings.has_avito_keys,
        "has_token": settings.has_avito_token,
        "has_credentials": settings.has_avito_keys,
        "avito_keys_configured": {
            "access_token": bool(settings.AVITO_ACCESS_TOKEN),
            "client_id": bool(settings.AVITO_CLIENT_ID),
            "client_secret": bool(settings.AVITO_CLIENT_SECRET)
        },
        "environment": settings.ENVIRONMENT,
        "message": "Avito API работает в демо-режиме. Укажите ключи для полной функциональности." if not settings.has_avito_keys else "Avito API полностью настроен"
    }