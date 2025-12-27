"""
API эндпоинты для быстрых ответов и шаблонов сообщений
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from ...core.database import get_db, SessionLocal
from ...core.security import get_current_user, is_manager
from ...models import User
from ...services.quick_reply_service import QuickReplyService, get_available_variables, validate_template_content

logger = logging.getLogger(__name__)

router = APIRouter()
quick_reply_service = QuickReplyService()

@router.get("/templates")
async def get_all_templates(
    current_user: User = Depends(get_current_user)
):
    """Получение всех шаблонов"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        templates = quick_reply_service.get_all_templates(current_user.id, db)
        return {"templates": templates}
    finally:
        db.close()

@router.get("/templates/category/{category}")
async def get_templates_by_category(
    category: str,
    current_user: User = Depends(get_current_user)
):
    """Получение шаблонов по категории"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        templates = quick_reply_service.get_templates_by_category(category, current_user.id, db)
        return {"templates": templates}
    finally:
        db.close()

@router.get("/templates/popular")
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Получение популярных шаблонов"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        templates = quick_reply_service.get_popular_templates(limit, current_user.id, db)
        return {"templates": templates}
    finally:
        db.close()

@router.get("/templates/search")
async def search_templates(
    q: str = Query(..., description="Поисковый запрос"),
    current_user: User = Depends(get_current_user)
):
    """Поиск шаблонов"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        templates = quick_reply_service.search_templates(q, current_user.id, db)
        return {"templates": templates}
    finally:
        db.close()

@router.get("/variables")
async def get_available_variables():
    """Получение списка доступных переменных"""
    variables = get_available_variables()
    return {"variables": variables}

@router.post("/templates")
async def create_template(
    template_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Создание нового шаблона"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # Валидация данных
    title = template_data.get("title", "").strip()
    content = template_data.get("content", "").strip()
    category = template_data.get("category", "").strip()
    
    if not title or not content or not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Все поля обязательны для заполнения"
        )
    
    # Валидация содержимого
    validation = validate_template_content(content)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибки валидации: {', '.join(validation['errors'])}"
        )
    
    db = SessionLocal()
    try:
        result = quick_reply_service.create_template(
            title=title,
            content=content,
            category=category,
            manager_id=current_user.id,
            db=db
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    template_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Обновление шаблона"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # Валидация данных
    title = template_data.get("title", "").strip()
    content = template_data.get("content", "").strip()
    category = template_data.get("category", "").strip()
    
    if not title or not content or not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Все поля обязательны для заполнения"
        )
    
    # Валидация содержимого
    validation = validate_template_content(content)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибки валидации: {', '.join(validation['errors'])}"
        )
    
    db = SessionLocal()
    try:
        result = quick_reply_service.update_template(
            template_id=template_id,
            title=title,
            content=content,
            category=category,
            db=db
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user)
):
    """Удаление шаблона"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    db = SessionLocal()
    try:
        result = quick_reply_service.delete_template(template_id, db)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
    finally:
        db.close()

@router.post("/templates/{template_id}/format")
async def format_template(
    template_id: str,
    variables: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Форматирование шаблона с переменными"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # Получаем содержимое шаблона
    template_content = None
    is_default = template_id.startswith("default_")
    
    if is_default:
        # Поиск в шаблонах по умолчанию
        for template in quick_reply_service.get_default_templates():
            if f"default_{template['title'].lower().replace(' ', '_')}" == template_id:
                template_content = template["content"]
                break
    else:
        # Поиск в пользовательских шаблонах
        from ...models import QuickReply
        db = SessionLocal()
        try:
            template = db.query(QuickReply).filter(QuickReply.id == template_id).first()
            if template:
                template_content = template.content
        finally:
            db.close()
    
    if not template_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден"
        )
    
    # Форматируем шаблон
    formatted = quick_reply_service.format_template(template_content, variables)
    
    # Увеличиваем счетчик использования (только для пользовательских шаблонов)
    if not is_default:
        db = SessionLocal()
        try:
            quick_reply_service.increment_usage(template_id, db)
        finally:
            db.close()
    
    return {"formatted_content": formatted}

@router.get("/defaults")
async def get_default_templates():
    """Получение шаблонов по умолчанию"""
    templates = quick_reply_service.get_default_templates()
    return {"templates": templates}