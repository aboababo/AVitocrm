#!/usr/bin/env python3
"""
Скрипт для исправления приоритетов чатов в базе данных.
Проблема: значения хранятся в нижнем регистре, но код ожидает UPPERCASE.
"""

import sqlite3

def fix_chat_priorities():
    """Исправляет значения приоритетов в таблице chats"""
    
    db_path = 'backend/osagaming_crm.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Проверка текущих значений в таблице chats...")
        
        # Проверяем текущие значения приоритетов
        cursor.execute('SELECT DISTINCT priority FROM chats')
        distinct_priorities = cursor.fetchall()
        print(f'Текущие значения приоритетов: {distinct_priorities}')
        
        # Проверяем значения статусов
        cursor.execute('SELECT DISTINCT status FROM chats')
        distinct_statuses = cursor.fetchall()
        print(f'Текущие значения статусов: {distinct_statuses}')
        
        # Преобразуем приоритеты в UPPERCASE
        print("\nИсправление приоритетов...")
        priority_mapping = {
            'low': 'LOW',
            'normal': 'NORMAL', 
            'high': 'HIGH',
            'urgent': 'URGENT'
        }
        
        for old_priority, new_priority in priority_mapping.items():
            cursor.execute(
                "UPDATE chats SET priority = ? WHERE priority = ?",
                (new_priority, old_priority)
            )
            updated = cursor.rowcount
            if updated > 0:
                print(f"  {old_priority} -> {new_priority}: {updated} записей")
        
        # Преобразуем статусы в UPPERCASE  
        print("\nИсправление статусов...")
        status_mapping = {
            'active': 'ACTIVE',
            'pending': 'PENDING',
            'closed': 'CLOSED',
            'archived': 'ARCHIVED'
        }
        
        for old_status, new_status in status_mapping.items():
            cursor.execute(
                "UPDATE chats SET status = ? WHERE status = ?",
                (new_status, old_status)
            )
            updated = cursor.rowcount
            if updated > 0:
                print(f"  {old_status} -> {new_status}: {updated} записей")
        
        conn.commit()
        
        # Проверяем результат
        print("\nПроверка исправленных значений...")
        cursor.execute('SELECT DISTINCT priority FROM chats')
        fixed_priorities = cursor.fetchall()
        print(f'Исправленные приоритеты: {fixed_priorities}')
        
        cursor.execute('SELECT DISTINCT status FROM chats')
        fixed_statuses = cursor.fetchall()
        print(f'Исправленные статусы: {fixed_statuses}')
        
        # Подсчитываем общее количество чатов
        cursor.execute('SELECT COUNT(*) FROM chats')
        total_chats = cursor.fetchone()[0]
        print(f'\nВсего чатов в базе: {total_chats}')
        
        conn.close()
        
        print("\n✅ Исправление приоритетов и статусов завершено успешно!")
        print("Теперь можно перезапустить приложение:")
        print("  docker-compose down")
        print("  docker-compose up --build")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении приоритетов: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('=== Исправление приоритетов чатов в базе данных ===')
    print('Значения будут преобразованы из нижнего регистра в UPPERCASE')
    print('Пример: "low" -> "LOW", "normal" -> "NORMAL"')
    print()
    
    fix_chat_priorities()