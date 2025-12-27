"""
API эндпоинты для управления пулом чатов
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ...core.database import get_db, SessionLocal
from ...core.security import get_current_user, is_admin, is_manager
from ...models import User
from ...services.chat_pool_service import ChatPoolService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/add-to-pool/{chat_id}")
async def add_chat_to_pool(
    chat_id: str,
    current_user: User = Depends(get_current_user)
):
    """Добавление чата в пул"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        result = pool_service.add_chat_to_pool(chat_id, db)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.post("/remove-from-pool/{chat_id}")
async def remove_chat_from_pool(
    chat_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление чата из пула"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        result = pool_service.remove_chat_from_pool(chat_id, db)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.post("/assign/{chat_id}/{manager_id}")
async def assign_chat_to_manager(
    chat_id: str,
    manager_id: int,
    current_user: User = Depends(get_current_user)
):
    """Назначение чата менеджеру"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        result = pool_service.assign_chat_to_manager(chat_id, manager_id, db)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.get("/available")
async def get_available_chats(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Получение доступных чатов для менеджера"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        chats = pool_service.get_available_chats_for_manager(current_user.id, limit, db)
        
        return {"chats": chats}
    finally:
        db.close()

@router.post("/release/{chat_id}")
async def release_chat_from_manager(
    chat_id: str,
    current_user: User = Depends(get_current_user)
):
    """Освобождение чата от менеджера"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        result = pool_service.release_chat_from_manager(chat_id, db)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.post("/auto-assign")
async def auto_assign_chats(
    current_user: User = Depends(get_current_user)
):
    """Автоматическое назначение чатов"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        result = pool_service.auto_assign_chats(db)
        
        return result
    finally:
        db.close()

@router.get("/statistics")
async def get_pool_statistics(
    current_user: User = Depends(get_current_user)
):
    """Получение статистики пула"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        pool_service = ChatPoolService()
        stats = pool_service.get_pool_statistics(db)
        
        return stats
    finally:
        db.close()