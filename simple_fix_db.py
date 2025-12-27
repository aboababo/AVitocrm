#!/usr/bin/env python3
"""
Простое исправление корневой базы данных для совместимости
"""

import sqlite3
import os

def fix_database():
    """Исправляет базу данных в корне проекта"""
    
    db_path = 'osagaming_crm.db'
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        return False
    
    print("Исправление базы данных...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Проверяем таблицу users
    print("1. Проверяем таблицу users...")
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"   Колонки: {', '.join(columns)}")
    
    # Проверяем наличие колонок
    has_password = 'password' in columns
    has_hashed_password = 'hashed_password' in columns
    
    if has_password and not has_hashed_password:
        print("   Нужно переименовать password -> hashed_password")
        
        try:
            # Создаем новую таблицу
            cursor.execute('''
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    bio TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    is_superuser BOOLEAN NOT NULL DEFAULT 0,
                    is_verified BOOLEAN NOT NULL DEFAULT 0,
                    avatar_url TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    last_login TIMESTAMP,
                    email_notifications BOOLEAN DEFAULT 1,
                    push_notifications BOOLEAN DEFAULT 1,
                    kpi_score DECIMAL(5,2) DEFAULT 0,
                    salary DECIMAL(10,2) DEFAULT 0,
                    temp_password TEXT,
                    password_changed BOOLEAN DEFAULT 0
                )
            ''')
            
            # Копируем данные
            cursor.execute('SELECT * FROM users')
            users = cursor.fetchall()
            print(f"   Найдено пользователей: {len(users)}")
            
            for user in users:
                # Старые данные: id, username, email, password, role, is_active, salary, kpi_score, temp_password, password_changed, created_at, created_by, settings, first_name, last_name
                cursor.execute('''
                    INSERT INTO users_new (id, email, hashed_password, first_name, status, is_active, is_superuser, 
                                          salary, kpi_score, temp_password, password_changed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user[0],  # id
                    user[2],  # email
                    user[3],  # password -> hashed_password
                    user[1],  # username -> first_name
                    'ACTIVE' if (user[5] if len(user) > 5 else 1) else 'INACTIVE',
                    user[5] if len(user) > 5 else 1,  # is_active
                    1 if (user[4] if len(user) > 4 else 'user') == 'super_admin' else 0,  # is_superuser
                    user[6] if len(user) > 6 else 0,  # salary
                    user[7] if len(user) > 7 else 0,  # kpi_score
                    user[8] if len(user) > 8 else None,  # temp_password
                    user[9] if len(user) > 9 else 0,  # password_changed
                    user[10] if len(user) > 10 else '2025-01-01 00:00:00'  # created_at
                ))
            
            # Удаляем старую и переименовываем новую
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            print("   Таблица users исправлена")
            
        except Exception as e:
            print(f"   Ошибка: {e}")
            conn.rollback()
            return False
    
    # 2. Проверяем таблицу chats
    print("\n2. Проверяем таблицу chats...")
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if cursor.fetchone():
            # Исправляем регистр статусов и приоритетов
            print("   Исправляем регистр status и priority...")
            
            # Обновляем status
            cursor.execute("UPDATE chats SET status = UPPER(status) WHERE LOWER(status) = status")
            updated_status = cursor.rowcount
            print(f"   Обновлено статусов: {updated_status}")
            
            # Обновляем priority
            cursor.execute("UPDATE chats SET priority = UPPER(priority) WHERE LOWER(priority) = priority")
            updated_priority = cursor.rowcount
            print(f"   Обновлено приоритетов: {updated_priority}")
            
            # Проверяем сколько чатов
            cursor.execute("SELECT COUNT(*) FROM chats")
            chat_count = cursor.fetchone()[0]
            print(f"   Всего чатов: {chat_count}")
            
        else:
            print("   Таблица chats не найдена")
    except Exception as e:
        print(f"   Ошибка работы с chats: {e}")
    
    # 3. Фиксируем изменения
    conn.commit()
    
    # 4. Проверяем результат
    print("\n3. Проверяем результат...")
    
    # Проверяем пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"   Пользователей: {user_count}")
    
    cursor.execute("SELECT email, status FROM users LIMIT 3")
    users = cursor.fetchall()
    for user in users:
        print(f"   Пользователь: {user[0]}, Статус: {user[1]}")
    
    # Проверяем чаты
    try:
        cursor.execute("SELECT COUNT(*) FROM chats")
        chat_count = cursor.fetchone()[0]
        print(f"   Чатов: {chat_count}")
        
        if chat_count > 0:
            cursor.execute("SELECT client_name, status, priority FROM chats LIMIT 3")
            chats = cursor.fetchall()
            for chat in chats:
                print(f"   Чат: {chat[0]}, Статус: {chat[1]}, Приоритет: {chat[2]}")
    except:
        print("   Чатов нет или ошибка")
    
    conn.close()
    
    print("\n[SUCCESS] База данных исправлена!")
    print("Теперь можно перезапустить приложение:")
    print("  docker-compose down")
    print("  docker-compose up --build -d")
    
    return True

if __name__ == '__main__':
    print("=== Исправление корневой базы данных ===")
    print("Цель: сделать базу osagaming_crm.db совместимой с приложением")
    print()
    
    fix_database()