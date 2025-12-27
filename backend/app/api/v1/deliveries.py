"""
API эндпоинты для работы с доставками
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ...core.database import get_db, SessionLocal
from ...core.security import get_current_user, is_admin, is_manager
from ...models import User, Chat, Delivery, DeliveryStatus, ChatPriority

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_deliveries(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_user)
):
    """Получение списка доставок"""
    db = SessionLocal()
    try:
        query = db.query(Delivery).outerjoin(Chat).outerjoin(User)
        
        # Фильтрация по ролям
        if not is_admin(current_user):
            # Менеджеры видят только свои доставки
            query = query.filter(
                or_(
                    Delivery.chat_id == None,  # Доставки без чатов видят все
                    Chat.assigned_manager_id == current_user.id
                )
            )
        
        # Фильтрация по статусу
        if status_filter:
            try:
                status_enum = DeliveryStatus(status_filter)
                query = query.filter(Delivery.delivery_status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Неверный статус: {status_filter}"
                )
        
        # Подсчет общего количества
        total_count = query.count()
        
        # Получение результатов с пагинацией
        deliveries = query.order_by(
            Delivery.updated_at.desc()
        ).offset(offset).limit(limit).all()
        
        result = []
        for delivery in deliveries:
            delivery_data = {
                "id": delivery.id,
                "chat_id": delivery.chat_id,
                "delivery_status": delivery.delivery_status.value,
                "tracking_number": delivery.tracking_number,
                "carrier": delivery.carrier,
                "address": delivery.address,
                "city": delivery.city,
                "postal_code": delivery.postal_code,
                "country": delivery.country,
                "recipient_name": delivery.recipient_name,
                "recipient_phone": delivery.recipient_phone,
                "delivery_cost": delivery.delivery_cost,
                "delivery_weight": delivery.delivery_weight,
                "shipped_at": delivery.shipped_at,
                "delivered_at": delivery.delivered_at,
                "estimated_delivery": delivery.estimated_delivery,
                "notes": delivery.notes,
                "instructions": delivery.instructions,
                "created_at": delivery.created_at,
                "updated_at": delivery.updated_at,
                "is_delivered": delivery.is_delivered,
                "is_shipped": delivery.is_shipped,
                "full_address": delivery.full_address,
                "days_in_transit": delivery.days_in_transit
            }
            
            # Добавляем информацию о чате, если есть
            if delivery.chat:
                delivery_data["chat"] = {
                    "id": delivery.chat.id,
                    "client_name": delivery.chat.client_name,
                    "client_phone": delivery.chat.client_phone,
                    "listing_id": delivery.chat.listing_id,
                    "product_url": delivery.chat.product_url
                }
            
            result.append(delivery_data)
        
        return {
            "deliveries": result,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения доставок: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения доставок"
        )
    finally:
        db.close()

@router.post("/")
async def create_delivery(
    delivery_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Создание новой доставки"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания доставок"
        )
    
    db = SessionLocal()
    try:
        # Валидация данных
        chat_id = delivery_data.get("chat_id")
        address = delivery_data.get("address")
        recipient_name = delivery_data.get("recipient_name")
        status = delivery_data.get("delivery_status", "processing")
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Адрес доставки обязателен"
            )
        
        # Проверяем статус
        try:
            status_enum = DeliveryStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный статус: {status}"
            )
        
        # Создаем доставку
        delivery = Delivery(
            chat_id=chat_id,
            delivery_status=status_enum,
            tracking_number=delivery_data.get("tracking_number"),
            carrier=delivery_data.get("carrier"),
            address=address,
            city=delivery_data.get("city"),
            postal_code=delivery_data.get("postal_code"),
            country=delivery_data.get("country"),
            recipient_name=recipient_name,
            recipient_phone=delivery_data.get("recipient_phone"),
            delivery_cost=delivery_data.get("delivery_cost"),
            delivery_weight=delivery_data.get("delivery_weight"),
            estimated_delivery=delivery_data.get("estimated_delivery"),
            notes=delivery_data.get("notes"),
            instructions=delivery_data.get("instructions")
        )
        
        db.add(delivery)
        
        # Обновляем приоритет чата на "delivery", если указан chat_id
        if chat_id:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.priority = ChatPriority.HIGH
                chat.update_activity()
        
        db.commit()
        db.refresh(delivery)
        
        return {
            "id": delivery.id,
            "delivery_status": delivery.delivery_status.value,
            "message": "Доставка создана успешно"
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания доставки: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания доставки"
        )
    finally:
        db.close()

@router.put("/{delivery_id}")
async def update_delivery(
    delivery_id: int,
    delivery_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Обновление доставки"""
    if not is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для обновления доставок"
        )
    
    db = SessionLocal()
    try:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Доставка не найдена"
            )
        
        # Проверяем права доступа (только создатель или админ)
        if not is_admin(current_user):
            # Для менеджеров - проверяем, что это их доставка или доставка их чата
            if delivery.chat and delivery.chat.assigned_manager_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для обновления этой доставки"
                )
        
        # Обновляем поля
        if "delivery_status" in delivery_data:
            try:
                delivery.delivery_status = DeliveryStatus(delivery_data["delivery_status"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Неверный статус: {delivery_data['delivery_status']}"
                )
        
        if "tracking_number" in delivery_data:
            delivery.tracking_number = delivery_data["tracking_number"]
        if "carrier" in delivery_data:
            delivery.carrier = delivery_data["carrier"]
        if "address" in delivery_data:
            delivery.address = delivery_data["address"]
        if "city" in delivery_data:
            delivery.city = delivery_data["city"]
        if "postal_code" in delivery_data:
            delivery.postal_code = delivery_data["postal_code"]
        if "country" in delivery_data:
            delivery.country = delivery_data["country"]
        if "recipient_name" in delivery_data:
            delivery.recipient_name = delivery_data["recipient_name"]
        if "recipient_phone" in delivery_data:
            delivery.recipient_phone = delivery_data["recipient_phone"]
        if "delivery_cost" in delivery_data:
            delivery.delivery_cost = delivery_data["delivery_cost"]
        if "delivery_weight" in delivery_data:
            delivery.delivery_weight = delivery_data["delivery_weight"]
        if "estimated_delivery" in delivery_data:
            delivery.estimated_delivery = delivery_data["estimated_delivery"]
        if "notes" in delivery_data:
            delivery.notes = delivery_data["notes"]
        if "instructions" in delivery_data:
            delivery.instructions = delivery_data["instructions"]
        
        # Специальная логика для статусов
        if delivery_data.get("delivery_status") == "shipped":
            delivery.mark_as_shipped(
                delivery_data.get("tracking_number"),
                delivery_data.get("carrier")
            )
        elif delivery_data.get("delivery_status") == "delivered":
            delivery.mark_as_delivered()
        elif delivery_data.get("delivery_status") == "cancelled":
            delivery.cancel_delivery(delivery_data.get("notes"))
        
        db.commit()
        
        return {
            "success": True,
            "message": "Доставка обновлена успешно"
        }
        
    except Exception as e:
        logger.error(f"Ошибка обновления доставки: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления доставки"
        )
    finally:
        db.close()

@router.put("/batch")
async def batch_update_deliveries(
    batch_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Массовое обновление доставок"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут выполнять массовое обновление"
        )
    
    db = SessionLocal()
    try:
        deliveries = batch_data.get("deliveries", [])
        if not deliveries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходим массив доставок"
            )
        
        updated_count = 0
        errors = []
        
        for delivery_data in deliveries:
            delivery_id = delivery_data.get("id")
            if not delivery_id:
                errors.append({"delivery": delivery_data, "error": "ID доставки обязателен"})
                continue
            
            try:
                delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
                if not delivery:
                    errors.append({"id": delivery_id, "error": "Доставка не найдена"})
                    continue
                
                # Обновляем статус, если указан
                if "delivery_status" in delivery_data:
                    try:
                        delivery.delivery_status = DeliveryStatus(delivery_data["delivery_status"])
                    except ValueError:
                        errors.append({"id": delivery_id, "error": f"Неверный статус: {delivery_data['delivery_status']}"})
                        continue
                
                # Обновляем трек-номер и перевозчика
                if "tracking_number" in delivery_data:
                    delivery.tracking_number = delivery_data["tracking_number"]
                if "carrier" in delivery_data:
                    delivery.carrier = delivery_data["carrier"]
                
                # Обновляем заметки
                if "notes" in delivery_data:
                    delivery.notes = delivery_data["notes"]
                
                # Специальная логика для статусов
                if delivery_data.get("delivery_status") == "shipped":
                    delivery.mark_as_shipped(
                        delivery_data.get("tracking_number"),
                        delivery_data.get("carrier")
                    )
                elif delivery_data.get("delivery_status") == "delivered":
                    delivery.mark_as_delivered()
                elif delivery_data.get("delivery_status") == "cancelled":
                    delivery.cancel_delivery(delivery_data.get("notes"))
                
                updated_count += 1
                
            except Exception as e:
                errors.append({"id": delivery_id, "error": str(e)})
        
        db.commit()
        
        return {
            "success": True,
            "updated_count": updated_count,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Ошибка массового обновления доставок: {e}")
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка массового обновления доставок"
        )
    finally:
        db.close()

@router.get("/{delivery_id}")
async def get_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user)
):
    """Получение детальной информации о доставке"""
    db = SessionLocal()
    try:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Доставка не найдена"
            )
        
        # Проверяем права доступа
        if not is_admin(current_user):
            if delivery.chat and delivery.chat.assigned_manager_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для просмотра этой доставки"
                )
        
        # Формируем ответ
        result = {
            "id": delivery.id,
            "chat_id": delivery.chat_id,
            "delivery_status": delivery.delivery_status.value,
            "tracking_number": delivery.tracking_number,
            "carrier": delivery.carrier,
            "address": delivery.address,
            "city": delivery.city,
            "postal_code": delivery.postal_code,
            "country": delivery.country,
            "recipient_name": delivery.recipient_name,
            "recipient_phone": delivery.recipient_phone,
            "delivery_cost": delivery.delivery_cost,
            "delivery_weight": delivery.delivery_weight,
            "shipped_at": delivery.shipped_at,
            "delivered_at": delivery.delivered_at,
            "estimated_delivery": delivery.estimated_delivery,
            "notes": delivery.notes,
            "instructions": delivery.instructions,
            "created_at": delivery.created_at,
            "updated_at": delivery.updated_at,
            "is_delivered": delivery.is_delivered,
            "is_shipped": delivery.is_shipped,
            "full_address": delivery.full_address,
            "days_in_transit": delivery.days_in_transit
        }
        
        # Добавляем информацию о чате
        if delivery.chat:
            result["chat"] = {
                "id": delivery.chat.id,
                "client_name": delivery.chat.client_name,
                "client_phone": delivery.chat.client_phone,
                "client_email": delivery.chat.client_email,
                "listing_id": delivery.chat.listing_id,
                "product_url": delivery.chat.product_url,
                "status": delivery.chat.status.value if delivery.chat.status else None
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения доставки: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения доставки"
        )
    finally:
        db.close()

@router.get("/statistics/overview")
async def get_delivery_statistics(
    current_user: User = Depends(get_current_user)
):
    """Получение статистики по доставкам"""
    db = SessionLocal()
    try:
        query = db.query(Delivery).outerjoin(Chat)
        
        # Фильтрация по ролям
        if not is_admin(current_user):
            query = query.filter(
                or_(
                    Delivery.chat_id == None,
                    Chat.assigned_manager_id == current_user.id
                )
            )
        
        total_deliveries = query.count()
        
        # Статистика по статусам
        status_stats = db.query(
            Delivery.delivery_status,
            func.count(Delivery.id).label('count')
        ).outerjoin(Chat).filter(
            or_(
                Delivery.chat_id == None,
                Chat.assigned_manager_id == current_user.id if not is_admin(current_user) else True
            )
        ).group_by(Delivery.delivery_status).all()
        
        # Среднее время доставки
        avg_delivery_time = db.query(
            func.avg(func.extract('epoch', Delivery.delivered_at - Delivery.shipped_at) / 86400)
        ).filter(
            Delivery.delivered_at.isnot(None),
            Delivery.shipped_at.isnot(None)
        ).scalar()
        
        # Доставки в пути
        in_transit = db.query(Delivery).filter(
            Delivery.delivery_status.in_([
                DeliveryStatus.SHIPPED,
                DeliveryStatus.IN_TRANSIT,
                DeliveryStatus.OUT_FOR_DELIVERY
            ])
        ).count()
        
        # Просроченные доставки (не доставлены в срок)
        overdue = db.query(Delivery).filter(
            and_(
                Delivery.estimated_delivery < datetime.utcnow(),
                Delivery.delivered_at.is_(None),
                Delivery.delivery_status != DeliveryStatus.CANCELLED
            )
        ).count()
        
        return {
            "total_deliveries": total_deliveries,
            "status_statistics": [
                {"status": stat.delivery_status.value, "count": stat.count}
                for stat in status_stats
            ],
            "in_transit": in_transit,
            "overdue": overdue,
            "average_delivery_days": round(avg_delivery_time, 1) if avg_delivery_time else None
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики доставок: {e}")
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики доставок"
        )
    finally:
        db.close()