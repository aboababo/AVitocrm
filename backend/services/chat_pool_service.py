"""
Сервис пула чатов
Управление распределением чатов между менеджерами
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json

from ..models import Chat, Message, User, ChatAssignment, ChatStatus
from ..core.database import get_db

logger = logging.getLogger(__name__)

class ChatPoolService:
    """Сервис управления пулом чатов"""
    
    def __init__(self):
        self.assignment_timeout = timedelta(minutes=30)  # Таймаут назначения
        self.max_assignments_per_manager = 10  # Максимум чатов на менеджера
    
    def add_chat_to_pool(self, chat_id: str, db: Session) -> Dict[str, Any]:
        """Добавление чата в пул"""
        try:
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            if not chat:
                # Создаем новый чат
                chat = Chat(
                    chat_id=chat_id,
                    status=ChatStatus.PENDING,
                    is_in_pool=True,
                    created_at=datetime.utcnow()
                )
                db.add(chat)
            else:
                chat.is_in_pool = True
                chat.status = ChatStatus.PENDING
                if chat.assigned_manager_id:
                    # Убираем предыдущее назначение
                    assignment = db.query(ChatAssignment).filter(
                        ChatAssignment.chat_id == chat_id,
                        ChatAssignment.is_active == True
                    ).first()
                    if assignment:
                        assignment.is_active = False
                        assignment.ended_at = datetime.utcnow()
                
                chat.assigned_manager_id = None
            
            db.commit()
            db.refresh(chat)
            
            logger.info(f"✅ Чат {chat_id} добавлен в пул")
            return {"chat_id": chat_id, "status": "added_to_pool"}
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления чата в пул: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def remove_chat_from_pool(self, chat_id: str, db: Session) -> Dict[str, Any]:
        """Удаление чата из пула"""
        try:
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            if chat:
                chat.is_in_pool = False
                if chat.status == ChatStatus.PENDING:
                    chat.status = ChatStatus.ACTIVE
                db.commit()
                
                logger.info(f"✅ Чат {chat_id} удален из пула")
                return {"chat_id": chat_id, "status": "removed_from_pool"}
            else:
                return {"error": "Chat not found"}
                
        except Exception as e:
            logger.error(f"❌ Ошибка удаления чата из пула: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def assign_chat_to_manager(self, chat_id: str, manager_id: int, db: Session) -> Dict[str, Any]:
        """Назначение чата менеджеру"""
        try:
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            if not chat:
                return {"error": "Chat not found"}
            
            # Проверяем, не заблокирован ли чат
            if chat.status == ChatStatus.BLOCKED:
                return {"error": "Chat is blocked"}
            
            # Проверяем количество активных чатов у менеджера
            active_chats_count = db.query(Chat).filter(
                Chat.assigned_manager_id == manager_id,
                Chat.status != ChatStatus.BLOCKED,
                Chat.status != ChatStatus.CLOSED
            ).count()
            
            if active_chats_count >= self.max_assignments_per_manager:
                return {"error": f"Manager has maximum number of chats ({self.max_assignments_per_manager})"}
            
            # Завершаем предыдущие назначения
            previous_assignments = db.query(ChatAssignment).filter(
                ChatAssignment.chat_id == chat_id,
                ChatAssignment.is_active == True
            ).all()
            
            for assignment in previous_assignments:
                assignment.is_active = False
                assignment.ended_at = datetime.utcnow()
            
            # Создаем новое назначение
            new_assignment = ChatAssignment(
                chat_id=chat_id,
                manager_id=manager_id,
                assigned_at=datetime.utcnow(),
                is_active=True
            )
            db.add(new_assignment)
            
            # Обновляем чат
            chat.assigned_manager_id = manager_id
            chat.status = ChatStatus.ACTIVE
            chat.is_in_pool = False
            chat.last_assigned_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"✅ Чат {chat_id} назначен менеджеру {manager_id}")
            return {
                "chat_id": chat_id,
                "manager_id": manager_id,
                "status": "assigned"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка назначения чата: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def get_available_chats_for_manager(self, manager_id: int, limit: int = 20, db: Session = None) -> List[Dict[str, Any]]:
        """Получение доступных чатов для менеджера"""
        try:
            # Получаем чаты в пуле, не назначенные менеджеру
            available_chats = db.query(Chat).filter(
                Chat.is_in_pool == True,
                or_(
                    Chat.assigned_manager_id == None,
                    Chat.assigned_manager_id != manager_id
                ),
                Chat.status == ChatStatus.PENDING
            ).order_by(
                Chat.last_activity_at.desc()  # Сначала самые активные
            ).limit(limit).all()
            
            result = []
            for chat in available_chats:
                # Получаем последнее сообщение
                last_message = db.query(Message).filter(
                    Message.chat_id == chat.chat_id
                ).order_by(desc(Message.created_at)).first()
                
                result.append({
                    "chat_id": chat.chat_id,
                    "user_name": chat.user_name,
                    "listing_title": chat.listing_title,
                    "last_message": last_message.content if last_message else None,
                    "last_activity": chat.last_activity_at,
                    "created_at": chat.created_at,
                    "is_in_pool": chat.is_in_pool
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения доступных чатов: {e}")
            return []
    
    def release_chat_from_manager(self, chat_id: str, db: Session) -> Dict[str, Any]:
        """Освобождение чата от менеджера"""
        try:
            chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            if not chat:
                return {"error": "Chat not found"}
            
            # Завершаем активное назначение
            active_assignment = db.query(ChatAssignment).filter(
                ChatAssignment.chat_id == chat_id,
                ChatAssignment.is_active == True
            ).first()
            
            if active_assignment:
                active_assignment.is_active = False
                active_assignment.ended_at = datetime.utcnow()
            
            # Возвращаем чат в пул
            chat.assigned_manager_id = None
            chat.is_in_pool = True
            chat.status = ChatStatus.PENDING
            chat.last_released_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"✅ Чат {chat_id} возвращен в пул")
            return {
                "chat_id": chat_id,
                "status": "released_to_pool"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка освобождения чата: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def get_pool_statistics(self, db: Session) -> Dict[str, Any]:
        """Получение статистики пула"""
        try:
            total_chats = db.query(Chat).filter(Chat.is_in_pool == True).count()
            pending_chats = db.query(Chat).filter(
                Chat.is_in_pool == True,
                Chat.status == ChatStatus.PENDING
            ).count()
            
            # Статистика по менеджерам
            manager_stats = db.query(
                User.id,
                User.username,
                func.count(Chat.id).label('active_chats')
            ).join(
                Chat, User.id == Chat.assigned_manager_id
            ).filter(
                User.role == "manager",
                Chat.status != ChatStatus.BLOCKED,
                Chat.status != ChatStatus.CLOSED
            ).group_by(User.id, User.username).all()
            
            return {
                "total_in_pool": total_chats,
                "pending_chats": pending_chats,
                "manager_statistics": [
                    {
                        "manager_id": stat.id,
                        "username": stat.username,
                        "active_chats": stat.active_chats
                    }
                    for stat in manager_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики пула: {e}")
            return {}

    def auto_assign_chats(self, db: Session) -> Dict[str, Any]:
        """Автоматическое назначение чатов"""
        try:
            # Получаем менеджеров с наименьшей нагрузкой
            managers = db.query(User).filter(
                User.role == "manager",
                User.is_active == True
            ).all()
            
            assigned_count = 0
            
            for manager in managers:
                # Проверяем текущую нагрузку
                current_chats = db.query(Chat).filter(
                    Chat.assigned_manager_id == manager.id,
                    Chat.status != ChatStatus.BLOCKED,
                    Chat.status != ChatStatus.CLOSED
                ).count()
                
                if current_chats >= self.max_assignments_per_manager:
                    continue
                
                # Получаем доступные чаты
                available_chats = self.get_available_chats_for_manager(
                    manager.id, 
                    self.max_assignments_per_manager - current_chats,
                    db
                )
                
                # Назначаем чаты
                for chat_info in available_chats:
                    result = self.assign_chat_to_manager(
                        chat_info["chat_id"], 
                        manager.id, 
                        db
                    )
                    if "error" not in result:
                        assigned_count += 1
            
            logger.info(f"✅ Автоматически назначено {assigned_count} чатов")
            return {"assigned_chats": assigned_count}
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического назначения: {e}")
            return {"error": str(e)}