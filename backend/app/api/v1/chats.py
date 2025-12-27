"""
API роуты для работы с чатами
Современная система управления чатами
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import http
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc

from app.core.database import SessionLocal
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.chat import Chat, Message, ChatStatus, ChatPriority
from app.schemas.chat import (
    ChatCreate, ChatResponse, ChatUpdate, ChatListResponse,
    ChatStatusUpdate, MessageCreate, MessageResponse,
    MessageListResponse, MessageReadUpdate, ChatStats,
    ChatStatusEnum, ChatPriorityEnum, MessageTypeEnum
)

router = APIRouter()


@router.get("", response_model=ChatListResponse)
async def get_chats(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    status: Optional[ChatStatus] = Query(None),
    priority: Optional[ChatPriority] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|last_message_at|priority)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Получение списка чатов с пагинацией и фильтрацией
    """
    
    # Для SQLite используем синхронную сессию
    session = SessionLocal()
    
    try:
        # Базовый запрос
        query = session.query(Chat).filter(Chat.user_id == current_user.id)
        
        # Применение фильтров
        if status:
            query = query.filter(Chat.status == status)
        
        if priority:
            query = query.filter(Chat.priority == priority)
        
        if search:
            search_pattern = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    Chat.client_name.ilike(search_pattern),
                    Chat.title.ilike(search_pattern),
                    Chat.description.ilike(search_pattern)
                )
            )
        
        # Подсчет общего количества
        count_query = session.query(func.count(Chat.id)).filter(Chat.user_id == current_user.id)
        
        # Применение фильтров к count_query
        if status:
            count_query = count_query.filter(Chat.status == status)
        if priority:
            count_query = count_query.filter(Chat.priority == priority)
        if search:
            count_query = count_query.filter(
                or_(
                    Chat.client_name.ilike(search_pattern),
                    Chat.title.ilike(search_pattern),
                    Chat.description.ilike(search_pattern)
                )
            )
        
        total = count_query.scalar()
        
        # Сортировка
        sort_field = getattr(Chat, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # Пагинация
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Выполнение запроса
        chats = query.all()
        
        # Подготовка ответа - создаем ChatResponse вручную, т.к. from_orm не работает с enum
        chat_responses = []
        for chat in chats:
            chat_responses.append(ChatResponse(
                id=chat.id,
                user_id=chat.user_id,
                shop_id=chat.shop_id,
                chat_id=chat.chat_id,
                external_id=chat.external_id,
                customer_id=chat.customer_id,
                client_name=chat.client_name,
                client_phone=chat.client_phone,
                client_email=chat.client_email,
                client_location=chat.client_location,
                product_url=chat.product_url,
                listing_id=chat.listing_id,
                listing_data=chat.listing_data,
                status=chat.status.value,  # Явно берем значение enum как строку
                priority=chat.priority.value,  # Явно берем значение enum как строку
                title=chat.title,
                description=chat.description,
                tags=chat.tags,
                message_count=chat.message_count,
                unread_count=chat.unread_count,
                response_timer=chat.response_timer,
                last_message=chat.last_message,
                last_activity_at=chat.last_activity_at,
                assigned_manager_id=chat.assigned_manager_id,
                assigned_manager_name=chat.assigned_manager_name,
                is_in_pool=chat.is_in_pool,
                last_assigned_at=chat.last_assigned_at,
                last_released_at=chat.last_released_at,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                closed_at=chat.closed_at,
                is_unread=chat.unread_count > 0,
                is_urgent=chat.priority in [ChatPriority.HIGH, ChatPriority.URGENT],
                duration_minutes=chat.duration_minutes,
                client_display_name=chat.client_display_name
            ))
        
        session.close()
        
        return ChatListResponse(
            chats=chat_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    except Exception as e:
        session.close()
        print(f"Get chats error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при получении чатов"
        )
    

@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Создание нового чата
    """
    
    session = SessionLocal()
    
    try:
        new_chat = Chat(
            user_id=current_user.id,
            client_name=chat_data.client_name,
            client_phone=chat_data.client_phone,
            client_email=chat_data.client_email,
            client_location=chat_data.client_location,
            title=chat_data.title,
            description=chat_data.description,
            priority=chat_data.priority,
            status=ChatStatus.ACTIVE,
            message_count=0,
            unread_count=0
        )
        
        session.add(new_chat)
        session.commit()
        session.refresh(new_chat)
        
        # Создаем ChatResponse вручную для правильной обработки enum
        chat_response = ChatResponse(
            id=new_chat.id,
            user_id=new_chat.user_id,
            shop_id=new_chat.shop_id,
            chat_id=new_chat.chat_id,
            external_id=new_chat.external_id,
            customer_id=new_chat.customer_id,
            client_name=new_chat.client_name,
            client_phone=new_chat.client_phone,
            client_email=new_chat.client_email,
            client_location=new_chat.client_location,
            product_url=new_chat.product_url,
            listing_id=new_chat.listing_id,
            listing_data=new_chat.listing_data,
            status=new_chat.status.value if new_chat.status else ChatStatusEnum.ACTIVE,
            priority=new_chat.priority.value if new_chat.priority else ChatPriorityEnum.NORMAL,
            title=new_chat.title,
            description=new_chat.description,
            tags=new_chat.tags,
            message_count=new_chat.message_count or 0,
            unread_count=new_chat.unread_count or 0,
            response_timer=new_chat.response_timer,
            last_message=new_chat.last_message,
            last_activity_at=new_chat.last_activity_at,
            assigned_manager_id=new_chat.assigned_manager_id,
            assigned_manager_name=new_chat.assigned_manager_name,
            is_in_pool=new_chat.is_in_pool,
            last_assigned_at=new_chat.last_assigned_at,
            last_released_at=new_chat.last_released_at,
            created_at=new_chat.created_at,
            updated_at=new_chat.updated_at,
            closed_at=new_chat.closed_at,
            is_unread=(new_chat.unread_count or 0) > 0,
            is_urgent=new_chat.priority in [ChatPriority.HIGH, ChatPriority.URGENT] if new_chat.priority else False,
            duration_minutes=new_chat.duration_minutes,
            client_display_name=new_chat.client_display_name or new_chat.client_name or "Клиент",
            last_message_at=new_chat.last_message_at
        )
        
        session.close()
        return chat_response
        
    except Exception as e:
        session.close()
        print(f"Create chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при создании чата"
        )
    

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Получение чата по ID
    """
    
    session = SessionLocal()
    
    try:
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        # Создаем ChatResponse вручную для правильной обработки enum
        chat_response = ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            shop_id=chat.shop_id,
            chat_id=chat.chat_id,
            external_id=chat.external_id,
            customer_id=chat.customer_id,
            client_name=chat.client_name,
            client_phone=chat.client_phone,
            client_email=chat.client_email,
            client_location=chat.client_location,
            product_url=chat.product_url,
            listing_id=chat.listing_id,
            listing_data=chat.listing_data,
            status=chat.status.value if chat.status else ChatStatusEnum.ACTIVE,
            priority=chat.priority.value if chat.priority else ChatPriorityEnum.NORMAL,
            title=chat.title,
            description=chat.description,
            tags=chat.tags,
            message_count=chat.message_count or 0,
            unread_count=chat.unread_count or 0,
            response_timer=chat.response_timer,
            last_message=chat.last_message,
            last_activity_at=chat.last_activity_at,
            assigned_manager_id=chat.assigned_manager_id,
            assigned_manager_name=chat.assigned_manager_name,
            is_in_pool=chat.is_in_pool,
            last_assigned_at=chat.last_assigned_at,
            last_released_at=chat.last_released_at,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
            is_unread=(chat.unread_count or 0) > 0,
            is_urgent=chat.priority in [ChatPriority.HIGH, ChatPriority.URGENT] if chat.priority else False,
            duration_minutes=chat.duration_minutes,
            client_display_name=chat.client_display_name or chat.client_name or "Клиент",
            last_message_at=chat.last_message_at
        )
        
        session.close()
        return chat_response
        
    except Exception as e:
        session.close()
        print(f"Get chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при получении чата"
        )


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Обновление чата
    """
    
    session = SessionLocal()
    
    try:
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        # Обновление полей
        update_data = chat_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(chat, field):
                setattr(chat, field, value)
        
        session.commit()
        session.refresh(chat)
        
        # Создаем ChatResponse вручную для правильной обработки enum
        chat_response = ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            shop_id=chat.shop_id,
            chat_id=chat.chat_id,
            external_id=chat.external_id,
            customer_id=chat.customer_id,
            client_name=chat.client_name,
            client_phone=chat.client_phone,
            client_email=chat.client_email,
            client_location=chat.client_location,
            product_url=chat.product_url,
            listing_id=chat.listing_id,
            listing_data=chat.listing_data,
            status=chat.status.value if chat.status else ChatStatusEnum.ACTIVE,
            priority=chat.priority.value if chat.priority else ChatPriorityEnum.NORMAL,
            title=chat.title,
            description=chat.description,
            tags=chat.tags,
            message_count=chat.message_count or 0,
            unread_count=chat.unread_count or 0,
            response_timer=chat.response_timer,
            last_message=chat.last_message,
            last_activity_at=chat.last_activity_at,
            assigned_manager_id=chat.assigned_manager_id,
            assigned_manager_name=chat.assigned_manager_name,
            is_in_pool=chat.is_in_pool,
            last_assigned_at=chat.last_assigned_at,
            last_released_at=chat.last_released_at,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
            is_unread=(chat.unread_count or 0) > 0,
            is_urgent=chat.priority in [ChatPriority.HIGH, ChatPriority.URGENT] if chat.priority else False,
            duration_minutes=chat.duration_minutes,
            client_display_name=chat.client_display_name or chat.client_name or "Клиент",
            last_message_at=chat.last_message_at
        )
        
        session.close()
        return chat_response
        
    except Exception as e:
        session.close()
        print(f"Update chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при обновлении чата"
        )


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Удаление чата
    """
    
    session = SessionLocal()
    
    try:
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        session.delete(chat)
        session.commit()
        
        session.close()
        return {"message": "Чат успешно удален"}
        
    except Exception as e:
        session.close()
        print(f"Delete chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при удалении чата"
        )


@router.patch("/{chat_id}/status", response_model=ChatResponse)
async def update_chat_status(
    chat_id: int,
    status_update: ChatStatusUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Обновление статуса чата
    """
    
    session = SessionLocal()
    
    try:
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        # Обновление статуса с дополнительной логикой
        chat.status = status_update.status
        
        if status_update.status == ChatStatus.CLOSED:
            chat.closed_at = datetime.utcnow()
        elif chat.closed_at and status_update.status == ChatStatus.ACTIVE:
            # Переоткрытие чата
            chat.closed_at = None
        
        session.commit()
        session.refresh(chat)
        
        # Создаем ChatResponse вручную для правильной обработки enum
        chat_response = ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            shop_id=chat.shop_id,
            chat_id=chat.chat_id,
            external_id=chat.external_id,
            customer_id=chat.customer_id,
            client_name=chat.client_name,
            client_phone=chat.client_phone,
            client_email=chat.client_email,
            client_location=chat.client_location,
            product_url=chat.product_url,
            listing_id=chat.listing_id,
            listing_data=chat.listing_data,
            status=chat.status.value if chat.status else ChatStatusEnum.ACTIVE,
            priority=chat.priority.value if chat.priority else ChatPriorityEnum.NORMAL,
            title=chat.title,
            description=chat.description,
            tags=chat.tags,
            message_count=chat.message_count or 0,
            unread_count=chat.unread_count or 0,
            response_timer=chat.response_timer,
            last_message=chat.last_message,
            last_activity_at=chat.last_activity_at,
            assigned_manager_id=chat.assigned_manager_id,
            assigned_manager_name=chat.assigned_manager_name,
            is_in_pool=chat.is_in_pool,
            last_assigned_at=chat.last_assigned_at,
            last_released_at=chat.last_released_at,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
            is_unread=(chat.unread_count or 0) > 0,
            is_urgent=chat.priority in [ChatPriority.HIGH, ChatPriority.URGENT] if chat.priority else False,
            duration_minutes=chat.duration_minutes,
            client_display_name=chat.client_display_name or chat.client_name or "Клиент",
            last_message_at=chat.last_message_at
        )
        
        session.close()
        return chat_response
        
    except Exception as e:
        session.close()
        print(f"Update chat status error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при обновлении статуса чата"
        )


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_chat_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Получение сообщений чата
    """
    
    session = SessionLocal()
    
    try:
        # Проверка доступа к чату
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        # Получение сообщений с пагинацией
        query = session.query(Message).filter(Message.chat_id == chat_id)
        count_query = session.query(func.count(Message.id)).filter(Message.chat_id == chat_id)
        
        # Сортировка по времени создания (новые в конце)
        query = query.order_by(Message.created_at)
        
        # Подсчет общего количества
        total = count_query.scalar() or 0
        
        # Пагинация
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Выполнение запроса
        messages = query.all()
        
        # Подготовка ответа - создаем MessageResponse вручную
        message_responses = []
        for msg in messages:
            message_responses.append(MessageResponse(
                id=msg.id,
                chat_id=msg.chat_id,
                user_id=msg.user_id,
                content=msg.content,
                message_type=MessageTypeEnum(msg.message_type) if msg.message_type else MessageTypeEnum.TEXT,
                is_system=msg.is_system,
                is_read=msg.is_read,
                is_edited=msg.is_edited,
                attachment_url=msg.attachment_url,
                attachment_name=msg.attachment_name,
                attachment_size=msg.attachment_size,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
                read_at=msg.read_at,
                external_id=msg.external_id,
                is_from_user=msg.is_from_user,
                is_from_client=not msg.is_from_user,
                has_attachment=bool(msg.attachment_url),
                sender_name=msg.sender_name or (msg.user.full_name if msg.user else "Клиент") or "Неизвестно"
            ))
        
        session.close()
        
        return MessageListResponse(
            messages=message_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except Exception as e:
        session.close()
        print(f"Get chat messages error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при получении сообщений чата"
        )


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message(
    chat_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Создание нового сообщения
    """
    
    session = SessionLocal()
    
    try:
        # Проверка доступа к чату
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        # Создание сообщения
        new_message = Message(
            chat_id=chat_id,
            user_id=current_user.id,
            content=message_data.content,
            message_type=message_data.message_type,
            is_system=False,
            is_read=True  # Сообщения от пользователя считаются прочитанными
        )
        
        session.add(new_message)
        
        # Обновление статистики чата
        chat.message_count = chat.message_count + 1 if chat.message_count else 1
        chat.last_message_at = datetime.utcnow()
        
        session.commit()
        session.refresh(new_message)
        
        # Создаем MessageResponse вручную
        message_response = MessageResponse(
            id=new_message.id,
            chat_id=new_message.chat_id,
            user_id=new_message.user_id,
            content=new_message.content,
            message_type=MessageTypeEnum(new_message.message_type) if new_message.message_type else MessageTypeEnum.TEXT,
            is_system=new_message.is_system,
            is_read=new_message.is_read,
            is_edited=new_message.is_edited,
            attachment_url=new_message.attachment_url,
            attachment_name=new_message.attachment_name,
            attachment_size=new_message.attachment_size,
            created_at=new_message.created_at,
            updated_at=new_message.updated_at,
            read_at=new_message.read_at,
            external_id=new_message.external_id,
            is_from_user=new_message.is_from_user,
            is_from_client=not new_message.is_from_user,
            has_attachment=bool(new_message.attachment_url),
            sender_name=new_message.sender_name or (new_message.user.full_name if new_message.user else "Клиент") or "Неизвестно"
        )
        
        session.close()
        return message_response
        
    except Exception as e:
        session.close()
        print(f"Create message error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при создании сообщения"
        )


@router.patch("/{chat_id}/messages/read", response_model=dict)
async def mark_messages_as_read(
    chat_id: int,
    read_update: MessageReadUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Отметка сообщений как прочитанных
    """
    
    session = SessionLocal()
    
    try:
        # Проверка доступа к чату
        chat = session.query(Chat).filter(
            and_(Chat.id == chat_id, Chat.user_id == current_user.id)
        ).first()
        
        if not chat:
            session.close()
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )
        
        # Обновление статуса сообщений
        query = session.query(Message).filter(
            and_(
                Message.chat_id == chat_id,
                Message.id.in_(read_update.message_ids),
                Message.user_id.is_(None)  # Сообщения от клиентов
            )
        )
        
        messages = query.all()
        
        # Отметка как прочитанных
        updated_count = 0
        for message in messages:
            if not message.is_read:
                message.is_read = True
                message.read_at = datetime.utcnow()
                updated_count += 1
        
        # Обновление счетчика непрочитанных сообщений
        if updated_count > 0:
            chat.unread_count = max(0, (chat.unread_count or 0) - updated_count)
        
        session.commit()
        session.close()
        
        return {
            "message": "Сообщения отмечены как прочитанные",
            "updated_count": updated_count
        }
        
    except Exception as e:
        session.close()
        print(f"Mark messages as read error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при обновлении статуса сообщений"
        )


@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Получение статистики чатов
    """
    
    session = SessionLocal()
    
    try:
        # Подсчет по статусам
        status_counts = {}
        for status in ChatStatus:
            count = session.query(func.count(Chat.id)).filter(
                and_(Chat.user_id == current_user.id, Chat.status == status)
            ).scalar()
            # Преобразуем None в 0
            status_counts[status.value] = count if count is not None else 0
        
        # Подсчет срочных чатов
        urgent_chats_result = session.query(func.count(Chat.id)).filter(
            and_(
                Chat.user_id == current_user.id,
                Chat.priority.in_([ChatPriority.HIGH, ChatPriority.URGENT])
            )
        ).scalar()
        urgent_chats = urgent_chats_result if urgent_chats_result is not None else 0
        
        # Общее количество сообщений
        total_messages_result = session.query(func.count(Message.id)).join(Chat).filter(
            Chat.user_id == current_user.id
        ).scalar()
        total_messages = total_messages_result if total_messages_result is not None else 0
        
        # Непрочитанные сообщения
        unread_messages_result = session.query(func.count(Message.id)).join(Chat).filter(
            and_(
                Chat.user_id == current_user.id,
                Message.user_id.is_(None),  # Сообщения от клиентов
                Message.is_read == False
            )
        ).scalar()
        unread_messages = unread_messages_result if unread_messages_result is not None else 0
        
        session.close()
        
        return ChatStats(
            total_chats=status_counts.get("active", 0) + status_counts.get("pending", 0),
            active_chats=status_counts.get("active", 0),
            pending_chats=status_counts.get("pending", 0),
            closed_chats=status_counts.get("closed", 0),
            urgent_chats=urgent_chats,
            total_messages=total_messages,
            unread_messages=unread_messages,
            # Дополнительные метрики можно добавить позже
            avg_response_time_minutes=None,
            avg_chat_duration_minutes=None
        )
        
    except Exception as e:
        session.close()
        print(f"Get chat stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при получении статистики чатов"
        )