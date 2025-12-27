#!/usr/bin/env python3
"""
Скрипт для исправления всех enum значений в базе данных.
Проблема: значения хранятся в нижнем регистре, но Pydantic ожидает UPPERCASE.
"""

import sqlite3

def fix_all_enum_cases():
    """Исправляет регистр всех enum значений в базе данных"""
    
    db_path = 'backend/osagaming_crm.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== ИСПРАВЛЕНИЕ РЕГИСТРА ENUM В БАЗЕ ДАННЫХ ===")
        
        # 1. Таблица chats - исправляем status
        print("\n1. Исправляем статусы в таблице 'chats':")
        cursor.execute("UPDATE chats SET status = UPPER(status) WHERE LOWER(status) = status")
        updated_status = cursor.rowcount
        print(f"   Обновлено записей: {updated_status}")
        
        # Проверяем исправленные значения
        cursor.execute("SELECT DISTINCT status FROM chats ORDER BY status")
        unique_statuses = cursor.fetchall()
        print(f"   Уникальные статусы после исправления: {unique_statuses}")
        
        # 2. Таблица chats - исправляем priority
        print("\n2. Исправляем приоритеты в таблице 'chats':")
        cursor.execute("UPDATE chats SET priority = UPPER(priority) WHERE LOWER(priority) = priority")
        updated_priority = cursor.rowcount
        print(f"   Обновлено записей: {updated_priority}")
        
        # Проверяем исправленные значения
        cursor.execute("SELECT DISTINCT priority FROM chats ORDER BY priority")
        unique_priorities = cursor.fetchall()
        print(f"   Уникальные приоритеты после исправления: {unique_priorities}")
        
        # 3. Таблица users - исправляем status
        print("\n3. Исправляем статусы в таблице 'users':")
        cursor.execute("UPDATE users SET status = UPPER(status) WHERE LOWER(status) = status")
        updated_user_status = cursor.rowcount
        print(f"   Обновлено записей: {updated_user_status}")
        
        # Проверяем исправленные значения
        cursor.execute("SELECT DISTINCT status FROM users ORDER BY status")
        unique_user_statuses = cursor.fetchall()
        print(f"   Уникальные статусы пользователей после исправления: {unique_user_statuses}")
        
        # 4. Проверяем полное состояние
        print("\n4. Полная проверка исправленных данных:")
        
        # Чаты - примеры записей
        cursor.execute("SELECT id, client_name, status, priority FROM chats ORDER BY id LIMIT 5")
        sample_chats = cursor.fetchall()
        print("   Примеры чатов:")
        for chat in sample_chats:
            print(f"     ID:{chat[0]} - {chat[1]} - Статус: '{chat[2]}' - Приоритет: '{chat[3]}'")
        
        # Пользователи
        cursor.execute("SELECT id, email, status FROM users")
        users = cursor.fetchall()
        print("\n   Пользователи:")
        for user in users:
            print(f"     ID:{user[0]} - {user[1]} - Статус: '{user[2]}'")
        
        # Сообщения (если есть)
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        print(f"\n   Сообщений в базе: {message_count}")
        
        # Фиксируем изменения
        conn.commit()
        conn.close()
        
        print("\n✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("Все enum значения приведены к верхнему регистру.")
        
        print("\n=== ДЕЙСТВИЯ ДЛЯ ЗАВЕРШЕНИЯ ===")
        print("1. Перезапустите приложение:")
        print("   docker-compose down")
        print("   docker-compose up --build -d")
        print("\n2. Проверьте работу:")
        print("   Откройте http://localhost:8000")
        print("   Войдите: admin@osagaming.com / admin123")
        print("\n3. API чатов должен работать корректно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении базы данных: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    fix_all_enum_cases()