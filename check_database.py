#!/usr/bin/env python3
"""
Проверка базы данных для выявления проблем с enum
"""

import sqlite3

def check_database():
    """Проверка состояния базы данных"""
    
    db_path = 'backend/osagaming_crm.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== ПРОВЕРКА БАЗЫ ДАННЫХ ===")
        
        # 1. Таблица chats
        print("\n1. Таблица 'chats':")
        
        # Проверяем структуру
        cursor.execute("PRAGMA table_info(chats)")
        columns = cursor.fetchall()
        print("   Структура таблицы:")
        for col in columns:
            if col[1] in ['status', 'priority']:
                print(f"     {col[1]}: тип={col[2]}, дефолт={col[4]}")
        
        # Проверяем значения статусов
        cursor.execute("SELECT DISTINCT status FROM chats")
        statuses = cursor.fetchall()
        print(f"   Уникальные статусы: {statuses}")
        
        # Проверяем значения приоритетов
        cursor.execute("SELECT DISTINCT priority FROM chats")
        priorities = cursor.fetchall()
        print(f"   Уникальные приоритеты: {priorities}")
        
        # Показываем несколько примеров
        cursor.execute("SELECT id, client_name, status, priority FROM chats LIMIT 5")
        rows = cursor.fetchall()
        print("   Примеры записей:")
        for row in rows:
            print(f"     ID:{row[0]} - {row[1]} - Статус: '{row[2]}' - Приоритет: '{row[3]}'")
        
        # 2. Таблица users
        print("\n2. Таблица 'users':")
        
        cursor.execute("SELECT DISTINCT status FROM users")
        user_statuses = cursor.fetchall()
        print(f"   Уникальные статусы: {user_statuses}")
        
        cursor.execute("SELECT id, email, status FROM users")
        users = cursor.fetchall()
        print("   Пользователи:")
        for user in users:
            print(f"     ID:{user[0]} - {user[1]} - Статус: '{user[2]}'")
        
        # 3. Общее количество записей
        print("\n3. Статистика базы данных:")
        
        cursor.execute("SELECT COUNT(*) FROM chats")
        chat_count = cursor.fetchone()[0]
        print(f"   Чатов всего: {chat_count}")
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"   Пользователей: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        print(f"   Сообщений: {message_count}")
        
        # 4. Проверка проблем с регистром
        print("\n4. Проблемы с регистром (нижний vs верхний регистр):")
        
        # Собираем все значения в нижнем регистре
        all_lowercase_statuses = []
        all_lowercase_priorities = []
        
        for status, in statuses:
            if status and status.islower():
                all_lowercase_statuses.append(status)
        
        for priority, in priorities:
            if priority and priority.islower():
                all_lowercase_priorities.append(priority)
        
        for status, in user_statuses:
            if status and status.islower():
                print(f"   ❌ Статус пользователя '{status}' в нижнем регистре")
        
        if all_lowercase_statuses:
            print(f"   ❌ Статусы чатов в нижнем регистре: {all_lowercase_statuses}")
        
        if all_lowercase_priorities:
            print(f"   ❌ Приоритеты чатов в нижнем регистре: {all_lowercase_priorities}")
        
        # 5. Анализ проблемы
        print("\n5. Анализ проблемы:")
        print("   В логах видно, что Pydantic ожидает значения в верхнем регистре:")
        print("     'ACTIVE', 'PENDING', 'CLOSED', 'ARCHIVED'")
        print("   Но в базе данных хранятся значения в нижнем регистре:")
        print("     'active', 'pending', 'closed', 'archived'")
        print("\n   Решение: нужно обновить все записи в базе данных")
        
        conn.close()
        
        print("\n=== РЕКОМЕНДАЦИИ ===")
        print("1. Обновить все записи в таблице chats:")
        print("   UPDATE chats SET status = UPPER(status)")
        print("   UPDATE chats SET priority = UPPER(priority)")
        print("\n2. Обновить все записи в таблице users:")
        print("   UPDATE users SET status = UPPER(status)")
        print("\n3. Перезапустить приложение")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        return False

if __name__ == '__main__':
    check_database()