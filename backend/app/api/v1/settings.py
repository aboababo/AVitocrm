"""
API эндпоинты для работы с системными настройками
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import logging

from ...core.database import get_db, SessionLocal
from ...core.security import get_current_user
from ...models import User, SystemSetting, KPISetting, KPIHistory, WorkSchedule, Penalty, AutomationRule, Chat, Message
from ...services.quick_reply_service import get_available_variables

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/system")
async def get_system_settings(
    current_user: User = Depends(get_current_user)
):
    """Получение системных настроек"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра системных настроек"
        )
    
    db = SessionLocal()
    try:
        settings = db.query(SystemSetting).all()
        return {
            "settings": [
                {
                    "id": setting.id,
                    "key": setting.setting_key,
                    "value": setting.setting_value,
                    "type": setting.setting_type,
                    "description": setting.description,
                    "updated_at": setting.updated_at
                }
                for setting in settings
            ]
        }
    except Exception as e:
        logger.error(f"Ошибка получения настроек: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения настроек"
        )
    finally:
        db.close()

@router.post("/system")
async def create_system_setting(
    setting_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Создание системной настройки"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания настроек"
        )
    
    key = setting_data.get("key")
    value = setting_data.get("value")
    setting_type = setting_data.get("type", "string")
    description = setting_data.get("description")
    
    if not key or value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ключ и значение обязательны"
        )
    
    db = SessionLocal()
    try:
        # Проверяем, не существует ли уже такая настройка
        existing = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Настройка с таким ключом уже существует"
            )
        
        setting = SystemSetting(
            setting_key=key,
            setting_value=str(value),
            setting_type=setting_type,
            description=description
        )
        
        db.add(setting)
        db.commit()
        db.refresh(setting)
        
        return {
            "id": setting.id,
            "key": setting.setting_key,
            "value": setting.setting_value,
            "type": setting.setting_type,
            "description": setting.description
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания настройки: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания настройки"
        )
    finally:
        db.close()

@router.put("/system/{setting_id}")
async def update_system_setting(
    setting_id: int,
    setting_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Обновление системной настройки"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для обновления настроек"
        )
    
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Настройка не найдена"
            )
        
        value = setting_data.get("value")
        description = setting_data.get("description")
        
        if value is not None:
            setting.setting_value = str(value)
        
        if description is not None:
            setting.description = description
        
        db.commit()
        
        return {
            "id": setting.id,
            "key": setting.setting_key,
            "value": setting.setting_value,
            "type": setting.setting_type,
            "description": setting.description
        }
        
    except Exception as e:
        logger.error(f"Ошибка обновления настройки: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления настройки"
        )
    finally:
        db.close()

@router.delete("/system/{setting_id}")
async def delete_system_setting(
    setting_id: int,
    current_user: User = Depends(get_current_user)
):
    """Удаление системной настройки"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления настроек"
        )
    
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Настройка не найдена"
            )
        
        db.delete(setting)
        db.commit()
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Ошибка удаления настройки: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления настройки"
        )
    finally:
        db.close()

@router.get("/kpi-settings")
async def get_kpi_settings(
    current_user: User = Depends(get_current_user)
):
    """Получение настроек KPI"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра KPI настроек"
        )
    
    db = SessionLocal()
    try:
        kpi_settings = db.query(KPISetting).all()
        return {
            "kpi_settings": [
                {
                    "id": setting.id,
                    "parameter_name": setting.parameter_name,
                    "weight": setting.weight,
                    "min_value": setting.min_value,
                    "penalty_amount": setting.penalty_amount,
                    "bonus_amount": setting.bonus_amount,
                    "created_at": setting.created_at
                }
                for setting in kpi_settings
            ]
        }
    except Exception as e:
        logger.error(f"Ошибка получения KPI настроек: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения KPI настроек"
        )
    finally:
        db.close()

@router.post("/kpi-settings")
async def create_kpi_setting(
    kpi_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Создание настройки KPI"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания KPI настроек"
        )
    
    db = SessionLocal()
    try:
        setting = KPISetting(
            parameter_name=kpi_data["parameter_name"],
            weight=kpi_data.get("weight", 1.0),
            min_value=kpi_data.get("min_value", 0.0),
            penalty_amount=kpi_data.get("penalty_amount", 0.0),
            bonus_amount=kpi_data.get("bonus_amount", 0.0)
        )
        
        db.add(setting)
        db.commit()
        db.refresh(setting)
        
        return {
            "id": setting.id,
            "parameter_name": setting.parameter_name,
            "weight": setting.weight,
            "min_value": setting.min_value,
            "penalty_amount": setting.penalty_amount,
            "bonus_amount": setting.bonus_amount
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания KPI настройки: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания KPI настройки"
        )
    finally:
        db.close()

@router.get("/kpi-history/{user_id}")
async def get_kpi_history(
    user_id: int,
    period_start: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    period_end: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user)
):
    """Получение истории KPI пользователя"""
    db = SessionLocal()
    try:
        query = db.query(KPIHistory).filter(KPIHistory.user_id == user_id)
        
        if period_start:
            query = query.filter(KPIHistory.period_start >= period_start)
        if period_end:
            query = query.filter(KPIHistory.period_end <= period_end)
        
        kpi_history = query.order_by(KPIHistory.period_start.desc()).all()
        
        return {
            "kpi_history": [
                {
                    "id": record.id,
                    "period_start": record.period_start,
                    "period_end": record.period_end,
                    "response_time_avg": record.response_time_avg,
                    "conversion_rate": record.conversion_rate,
                    "customer_satisfaction": record.customer_satisfaction,
                    "messages_per_chat": record.messages_per_chat,
                    "total_score": record.total_score,
                    "bonus_amount": record.bonus_amount,
                    "penalty_amount": record.penalty_amount,
                    "created_at": record.created_at
                }
                for record in kpi_history
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения истории KPI: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения истории KPI"
        )
    finally:
        db.close()

@router.get("/work-schedules/{user_id}")
async def get_work_schedules(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Получение графика работы пользователя"""
    db = SessionLocal()
    try:
        schedules = db.query(WorkSchedule).filter(
            WorkSchedule.user_id == user_id,
            WorkSchedule.is_active == True
        ).all()
        
        return {
            "work_schedules": [
                {
                    "id": schedule.id,
                    "day_of_week": schedule.day_of_week,
                    "start_time": schedule.start_time,
                    "end_time": schedule.end_time,
                    "is_active": schedule.is_active
                }
                for schedule in schedules
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения графика работы: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения графика работы"
        )
    finally:
        db.close()

@router.post("/work-schedules")
async def create_work_schedule(
    schedule_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Создание графика работы"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания графика работы"
        )
    
    db = SessionLocal()
    try:
        schedule = WorkSchedule(
            user_id=schedule_data["user_id"],
            day_of_week=schedule_data["day_of_week"],
            start_time=schedule_data["start_time"],
            end_time=schedule_data["end_time"],
            is_active=schedule_data.get("is_active", True)
        )
        
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        
        return {
            "id": schedule.id,
            "user_id": schedule.user_id,
            "day_of_week": schedule.day_of_week,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "is_active": schedule.is_active
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания графика работы: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания графика работы"
        )
    finally:
        db.close()

@router.get("/penalties/{user_id}")
async def get_user_penalties(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Получение штрафов пользователя"""
    db = SessionLocal()
    try:
        penalties = db.query(Penalty).filter(
            Penalty.manager_id == user_id
        ).order_by(Penalty.created_at.desc()).all()
        
        return {
            "penalties": [
                {
                    "id": penalty.id,
                    "penalty_type": penalty.penalty_type,
                    "penalty_amount": penalty.penalty_amount,
                    "reason": penalty.reason,
                    "is_paid": penalty.is_paid,
                    "created_at": penalty.created_at,
                    "paid_at": penalty.paid_at
                }
                for penalty in penalties
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения штрафов: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения штрафов"
        )
    finally:
        db.close()

@router.get("/automation-rules")
async def get_automation_rules(
    current_user: User = Depends(get_current_user)
):
    """Получение правил автоматизации"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра правил автоматизации"
        )
    
    db = SessionLocal()
    try:
        rules = db.query(AutomationRule).filter(
            AutomationRule.is_active == True
        ).all()
        
        return {
            "automation_rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "trigger_type": rule.trigger_type,
                    "trigger_condition": rule.trigger_condition,
                    "action_type": rule.action_type,
                    "action_data": rule.action_data,
                    "is_active": rule.is_active,
                    "created_at": rule.created_at
                }
                for rule in rules
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения правил автоматизации: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения правил автоматизации"
        )
    finally:
        db.close()

@router.get("/dashboard-stats")
async def get_dashboard_statistics(
    current_user: User = Depends(get_current_user)
):
    """Получение общей статистики для дашборда"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра статистики"
        )
    
    db = SessionLocal()
    try:
        # Статистика пользователей
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        managers_count = db.query(User).filter(User.is_superuser == True).count()
        
        # Статистика чатов
        from app.models.chat import ChatStatus
        total_chats = db.query(func.count(Chat.id)).scalar() or 0
        active_chats = db.query(func.count(Chat.id)).filter(Chat.status == ChatStatus.ACTIVE).scalar() or 0
        pending_chats = db.query(func.count(Chat.id)).filter(Chat.status == ChatStatus.PENDING).scalar() or 0
        
        # Статистика сообщений
        total_messages = db.query(func.count(Message.id)).scalar() or 0
        unread_messages = db.query(func.count(Message.id)).filter(Message.is_read == False).scalar() or 0
        
        # Статистика объявлений
        chats_with_listings = db.query(func.count(Chat.id)).filter(
            Chat.listing_id.isnot(None)
        ).scalar() or 0
        
        # Последние активности (топ-5)
        recent_activities = db.query(Chat).order_by(
            Chat.last_activity_at.desc()
        ).limit(5).all()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "managers": managers_count
            },
            "chats": {
                "total": total_chats,
                "active": active_chats,
                "pending": pending_chats,
                "with_listings": chats_with_listings
            },
            "messages": {
                "total": total_messages,
                "unread": unread_messages
            },
            "recent_activities": [
                {
                    "id": chat.id,
                    "client_name": chat.client_name,
                    "last_message": chat.last_message_text,
                    "last_activity": chat.last_activity_at,
                    "status": chat.status.value if chat.status else None
                }
                for chat in recent_activities
            ]
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики"
        )

@router.get("/available-variables")
async def get_available_variables_endpoint():
    """Получение доступных переменных для быстрых ответов"""
    variables = get_available_variables()
    return {"variables": variables}