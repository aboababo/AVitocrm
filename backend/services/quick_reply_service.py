"""
Сервис быстрых ответов и шаблонов сообщений
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import re

from ..models import QuickReply, User

logger = logging.getLogger(__name__)

class QuickReplyService:
    """Сервис быстрых ответов"""
    
    def __init__(self):
        self.default_templates = [
            {
                "title": "Приветствие",
                "content": "Добрый день! Меня зовут {manager_name}, я менеджер по продажам. Чем могу помочь?",
                "category": "greeting"
            },
            {
                "title": "Уточнение деталей",
                "content": "Уточните, пожалуйста, какой именно товар вас интересует и в каком количестве?",
                "category": "clarification"
            },
            {
                "title": "Цена",
                "content": "Стоимость составляет {price} рублей. Возможна скидка при покупке от {min_quantity} штук.",
                "category": "price"
            },
            {
                "title": "Доставка",
                "content": "Доставка осуществляется по всей России. Стоимость доставки: {delivery_price} рублей. Срок: {delivery_time} дней.",
                "category": "delivery"
            },
            {
                "title": "Оплата",
                "content": "Оплата возможна наличными при получении, банковской картой или безналичным расчетом.",
                "category": "payment"
            },
            {
                "title": "Гарантия",
                "content": "На товар предоставляется гарантия {warranty_period} месяцев. Гарантийное обслуживание осуществляется в авторизованных сервисных центрах.",
                "category": "warranty"
            },
            {
                "title": "Наличие",
                "content": "Товар в наличии. Готов к отгрузке в течение {shipping_time} рабочих дней после подтверждения заказа.",
                "category": "availability"
            },
            {
                "title": "Возврат",
                "content": "Согласно законодательству РФ, возврат товара надлежащего качества возможен в течение 14 дней с момента покупки.",
                "category": "return"
            },
            {
                "title": "Документы",
                "content": "Предоставляем полный пакет документов: чек, накладная, сертификаты качества.",
                "category": "documents"
            },
            {
                "title": "Оптовые цены",
                "content": "Для оптовых покупателей действуют специальные цены. Отправьте заявку на {email} для получения прайс-листа.",
                "category": "wholesale"
            },
            {
                "title": "Прощание",
                "content": "Спасибо за обращение! Если возникнут дополнительные вопросы, обращайтесь. Хорошего дня!",
                "category": "farewell"
            }
        ]
    
    def get_default_templates(self) -> List[Dict[str, Any]]:
        """Получение шаблонов по умолчанию"""
        return self.default_templates
    
    def create_template(self, title: str, content: str, category: str, 
                       manager_id: Optional[int] = None, db: Session = None) -> Dict[str, Any]:
        """Создание нового шаблона"""
        try:
            template = QuickReply(
                title=title,
                content=content,
                category=category,
                manager_id=manager_id,
                is_active=True,
                usage_count=0,
                created_at=datetime.utcnow()
            )
            
            if db:
                db.add(template)
                db.commit()
                db.refresh(template)
            
            logger.info(f"✅ Создан шаблон: {title}")
            return {
                "id": template.id,
                "title": template.title,
                "content": template.content,
                "category": template.category
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания шаблона: {e}")
            if db:
                db.rollback()
            return {"error": str(e)}
    
    def get_templates_by_category(self, category: str, manager_id: Optional[int] = None, db: Session = None) -> List[Dict[str, Any]]:
        """Получение шаблонов по категории"""
        templates = []
        
        # Сначала добавляем шаблоны по умолчанию
        for template in self.default_templates:
            if template["category"] == category:
                templates.append({
                    "id": f"default_{template['title'].lower().replace(' ', '_')}",
                    "title": template["title"],
                    "content": template["content"],
                    "category": template["category"],
                    "is_default": True
                })
        
        # Затем пользовательские шаблоны
        if db:
            query = db.query(QuickReply).filter(
                QuickReply.category == category,
                QuickReply.is_active == True
            )
            
            if manager_id:
                query = query.filter(
                    or_(QuickReply.manager_id == manager_id, QuickReply.manager_id == None)
                )
            
            user_templates = query.order_by(QuickReply.usage_count.desc()).all()
            
            for template in user_templates:
                templates.append({
                    "id": template.id,
                    "title": template.title,
                    "content": template.content,
                    "category": template.category,
                    "usage_count": template.usage_count,
                    "is_default": False
                })
        
        return templates
    
    def get_all_templates(self, manager_id: Optional[int] = None, db: Session = None) -> Dict[str, List[Dict[str, Any]]]:
        """Получение всех шаблонов, сгруппированных по категориям"""
        categories = {
            "greeting": "Приветствие",
            "clarification": "Уточнение",
            "price": "Цена",
            "delivery": "Доставка",
            "payment": "Оплата",
            "warranty": "Гарантия",
            "availability": "Наличие",
            "return": "Возврат",
            "documents": "Документы",
            "wholesale": "Оптовые цены",
            "farewell": "Прощание"
        }
        
        result = {}
        
        for category_key, category_name in categories.items():
            result[category_key] = self.get_templates_by_category(category_key, manager_id, db)
        
        return result
    
    def format_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Форматирование шаблона с переменными"""
        try:
            formatted = template_content
            
            # Заменяем переменные
            for key, value in variables.items():
                placeholder = "{" + key + "}"
                formatted = formatted.replace(placeholder, str(value))
            
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования шаблона: {e}")
            return template_content
    
    def increment_usage(self, template_id: str, db: Session = None):
        """Увеличение счетчика использования шаблона"""
        try:
            if db and not template_id.startswith("default_"):
                template = db.query(QuickReply).filter(QuickReply.id == template_id).first()
                if template:
                    template.usage_count += 1
                    db.commit()
            
        except Exception as e:
            logger.error(f"❌ Ошибка увеличения счетчика: {e}")
            if db:
                db.rollback()
    
    def update_template(self, template_id: int, title: str, content: str, category: str, db: Session) -> Dict[str, Any]:
        """Обновление шаблона"""
        try:
            template = db.query(QuickReply).filter(QuickReply.id == template_id).first()
            if not template:
                return {"error": "Template not found"}
            
            template.title = title
            template.content = content
            template.category = category
            template.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"✅ Обновлен шаблон: {title}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления шаблона: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def delete_template(self, template_id: int, db: Session) -> Dict[str, Any]:
        """Удаление шаблона"""
        try:
            template = db.query(QuickReply).filter(QuickReply.id == template_id).first()
            if not template:
                return {"error": "Template not found"}
            
            db.delete(template)
            db.commit()
            
            logger.info(f"✅ Удален шаблон: {template.title}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления шаблона: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def search_templates(self, query: str, manager_id: Optional[int] = None, db: Session = None) -> List[Dict[str, Any]]:
        """Поиск шаблонов по тексту"""
        results = []
        
        # Поиск в шаблонах по умолчанию
        for template in self.default_templates:
            if (query.lower() in template["title"].lower() or 
                query.lower() in template["content"].lower()):
                results.append({
                    "id": f"default_{template['title'].lower().replace(' ', '_')}",
                    "title": template["title"],
                    "content": template["content"],
                    "category": template["category"],
                    "is_default": True
                })
        
        # Поиск в пользовательских шаблонах
        if db:
            search_query = db.query(QuickReply).filter(
                QuickReply.is_active == True,
                or_(
                    QuickReply.title.ilike(f"%{query}%"),
                    QuickReply.content.ilike(f"%{query}%")
                )
            )
            
            if manager_id:
                search_query = search_query.filter(
                    or_(QuickReply.manager_id == manager_id, QuickReply.manager_id == None)
                )
            
            user_templates = search_query.order_by(QuickReply.usage_count.desc()).all()
            
            for template in user_templates:
                results.append({
                    "id": template.id,
                    "title": template.title,
                    "content": template.content,
                    "category": template.category,
                    "usage_count": template.usage_count,
                    "is_default": False
                })
        
        return results
    
    def get_popular_templates(self, limit: int = 10, manager_id: Optional[int] = None, db: Session = None) -> List[Dict[str, Any]]:
        """Получение популярных шаблонов"""
        templates = []
        
        # Добавляем популярные шаблоны по умолчанию
        popular_defaults = [
            "greeting", "price", "delivery", "availability", "farewell"
        ]
        
        for category in popular_defaults:
            for template in self.default_templates:
                if template["category"] == category:
                    templates.append({
                        "id": f"default_{template['title'].lower().replace(' ', '_')}",
                        "title": template["title"],
                        "content": template["content"],
                        "category": template["category"],
                        "usage_count": 0,
                        "is_default": True
                    })
                    break
        
        # Добавляем популярные пользовательские шаблоны
        if db:
            query = db.query(QuickReply).filter(
                QuickReply.is_active == True
            ).order_by(QuickReply.usage_count.desc()).limit(limit)
            
            if manager_id:
                query = query.filter(
                    or_(QuickReply.manager_id == manager_id, QuickReply.manager_id == None)
                )
            
            user_templates = query.all()
            
            for template in user_templates:
                templates.append({
                    "id": template.id,
                    "title": template.title,
                    "content": template.content,
                    "category": template.category,
                    "usage_count": template.usage_count,
                    "is_default": False
                })
        
        return templates[:limit]

# Утилиты для работы с шаблонами
def get_available_variables() -> Dict[str, str]:
    """Получение списка доступных переменных"""
    return {
        "manager_name": "Имя менеджера",
        "price": "Цена товара",
        "min_quantity": "Минимальное количество",
        "delivery_price": "Стоимость доставки",
        "delivery_time": "Время доставки",
        "warranty_period": "Период гарантии",
        "shipping_time": "Время отгрузки",
        "email": "Email для связи",
        "phone": "Номер телефона",
        "company_name": "Название компании",
        "working_hours": "Часы работы",
        "chat_id": "ID чата",
        "user_name": "Имя пользователя",
        "listing_title": "Название объявления"
    }

def validate_template_content(content: str) -> Dict[str, Any]:
    """Валидация содержимого шаблона"""
    errors = []
    
    if len(content.strip()) < 5:
        errors.append("Содержимое слишком короткое (минимум 5 символов)")
    
    if len(content) > 5000:
        errors.append("Содержимое слишком длинное (максимум 5000 символов)")
    
    # Проверяем баланс скобок
    if content.count('{') != content.count('}'):
        errors.append("Небалансированные фигурные скобки в переменных")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }

def extract_variables_from_content(content: str) -> List[str]:
    """Извлечение переменных из содержимого шаблона"""
    import re
    pattern = r'\{([^}]+)\}'
    matches = re.findall(pattern, content)
    return list(set(matches))  # Убираем дубликаты