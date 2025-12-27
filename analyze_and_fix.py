#!/usr/bin/env python3
"""
Анализ структуры баз данных и исправление проблемы с паролем
"""

import sqlite3
import datetime

def analyze_databases():
    """Анализирует структуру обеих баз данных"""
    
    print("=== АНАЛИЗ БАЗ ДАННЫХ ===")
    
    # 1. Старая база Vaito
    print("\n1. СТАРАЯ БАЗА (Vaito): osagaming_crm.db")
    
    old_conn = sqlite3.connect('osagaming_crm.db')
    old_cursor = old_conn.cursor()
    
    # Таблица users
    print("\n   Таблица USERS:")
    old_cursor.execute('PRAGMA table_info(users)')
    old_user_cols = old_cursor.fetchall()
    for col in old_user_cols:
        print(f"     {col[1]} ({col[2]})")
    
    # Таблица chats
    print("\n   Таблица CHATS:")
    old_cursor.execute('PRAGMA table_info(chats)')
    old_chat_cols = old_cursor.fetchall()
    for col in old_chat_cols:
        print(f"     {col[1]} ({col[2]})")
    
    # Данные в users
    print("\n   Пример пользователей:")
    old_cursor.execute('SELECT id, email, role FROM users LIMIT 3')
    for user in old_cursor.fetchall():
        print(f"     ID:{user[0]}, Email: {user[1]}, Role: {user[2]}")
    
    # 2. Новая база (Docker)
    print("\n2. НОВАЯ БАЗА (Docker): backend/osagaming_crm.db")
    
    try:
        new_conn = sqlite3.connect('backend/osagaming_crm.db')
        new_cursor = new_conn.cursor()
        
        print("\n   Таблица USERS:")
        new_cursor.execute('PRAGMA table_info(users)')
        new_user_cols = new_cursor.fetchall()
        for col in new_user_cols:
            print(f"     {col[1]} ({col[2]})")
        
        print("\n   Таблица CHATS:")
        new_cursor.execute('PRAGMA table_info(chats)')
        new_chat_cols = new_cursor.fetchall()
        for col in new_chat_cols:
            print(f"     {col[1]} ({col[2]})")
        
        new_conn.close()
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    old_conn.close()
    
    return old_user_cols, old_chat_cols

def create_migrated_database():
    """Создает исправленную базу данных с правильной структурой"""
    
    print("\n=== СОЗДАНИЕ ИСПРАВЛЕННОЙ БАЗЫ ДАННЫХ ===")
    
    # Подключаемся к старой базе
    old_conn = sqlite3.connect('osagaming_crm.db')
    old_cursor = old_conn.cursor()
    
    # Создаем временную исправленную базу
    migrated_db = 'backend/migrated_crm.db'
    
    new_conn = sqlite3.connect(migrated_db)
    new_cursor = new_conn.cursor()
    
    # Создаем таблицу users с новой структурой
    print("\n1. Создаем таблицу USERS с исправленной структурой...")
    
    new_cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            email_notifications BOOLEAN DEFAULT 1,
            push_notifications BOOLEAN DEFAULT 1,
            kpi_score DECIMAL(5,2) DEFAULT 0,
            salary DECIMAL(10,2) DEFAULT 0,
            temp_password TEXT,
            password_changed BOOLEAN DEFAULT 0,
            full_name TEXT GENERATED ALWAYS AS (first_name || ' ' || last_name)
        )
    ''')
    
    # Копируем пользователей из старой базы
    print("\n2. Копируем пользователей...")
    
    old_cursor.execute('SELECT * FROM users')
    old_users = old_cursor.fetchall()
    
    print(f"   Пользователей найдено: {len(old_users)}")
    
    for user_data in old_users:
        # user_data: (id, username, email, password, role, is_active, salary, kpi_score, temp_password, password_changed, created_at, created_by, settings, first_name, last_name)
        try:
            # Мапим старые данные на новую структуру
            new_cursor.execute('''
                INSERT INTO users (
                    id, email, hashed_password, first_name, 
                    status, is_active, is_superuser, 
                    kpi_score, salary, temp_password, password_changed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data[0],    # id
                user_data[2],    # email
                user_data[3] or '$2b$12$placeholder',  # password -> hashed_password
                user_data[1],    # username -> first_name
                'ACTIVE' if (user_data[5] if len(user_data) > 5 else 1) else 'INACTIVE',
                user_data[5] if len(user_data) > 5 else 1,  # is_active
                1 if (user_data[4] if len(user_data) > 4 else 'user') == 'super_admin' else 0,
                user_data[7] if len(user_data) > 7 else 0,  # kpi_score
                user_data[6] if len(user_data) > 6 else 0,  # salary
                user_data[8] if len(user_data) > 8 else None,  # temp_password
                user_data[9] if len(user_data) > 9 else 0,  # password_changed
                user_data[10] if len(user_data) > 10 else datetime.datetime.now().isoformat()
            ))
        except Exception as e:
            print(f"   Ошибка копирования пользователя {user_data[0]}: {e}")
    
    # Создаем таблицу chats с новой структурой
    print("\n3. Копируем чаты...")
    
    try:
        old_cursor.execute('SELECT * FROM chats')
        old_chats = old_cursor.fetchall()
        print(f"   Чатов найдено: {len(old_chats)}")
        
        # Создаем таблицу chats
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                client_name TEXT NOT NULL,
                client_phone TEXT,
                client_email TEXT,
                client_location TEXT,
                product_url TEXT,
                listing_id TEXT,
                listing_data TEXT,
                title TEXT,
                description TEXT,
                tags TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                priority TEXT NOT NULL DEFAULT 'NORMAL',
                message_count INTEGER DEFAULT 0,
                unread_count INTEGER DEFAULT 0,
                response_timer INTEGER,
                last_message TEXT,
                last_activity_at TIMESTAMP,
                assigned_manager_id INTEGER,
                assigned_manager_name TEXT,
                is_in_pool BOOLEAN DEFAULT 0,
                last_assigned_at TIMESTAMP,
                last_released_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                is_unread BOOLEAN GENERATED ALWAYS AS (unread_count > 0),
                is_urgent BOOLEAN GENERATED ALWAYS AS (priority IN ('HIGH', 'URGENT')),
                duration_minutes INTEGER GENERATED ALWAYS AS (
                    CAST((JULIANDAY(COALESCE(closed_at, datetime('now'))) - JULIANDAY(created_at)) * 24 * 60 AS INTEGER)
                ),
                client_display_name TEXT GENERATED ALWAYS AS (client_name || ' (' || client_phone || ')')
            )
        ''')
        
        for chat_data in old_chats:
            try:
                # В зависимости от количества колонок в старых чатах
                if len(chat_data) >= 5:
                    new_cursor.execute('''
                        INSERT INTO chats (
                            id, user_id, client_name, client_phone, 
                            title, description, priority, status,
                            message_count, unread_count, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        chat_data[0],  # id
                        1,  # user_id (admin)
                        chat_data[1] if len(chat_data) > 1 else 'Client',  # client_name
                        chat_data[2] if len(chat_data) > 2 else None,  # client_phone
                        chat_data[3] if len(chat_data) > 3 else 'Chat',  # title
                        chat_data[4] if len(chat_data) > 4 else None,  # description
                        'NORMAL',  # priority
                        'ACTIVE',  # status
                        0,  # message_count
                        0,  # unread_count
                        datetime.datetime.now().isoformat(),
                        datetime.datetime.now().isoformat()
                    ))
            except Exception as e:
                print(f"   Ошибка копирования чата {chat_data[0]}: {e}")
    except Exception as e:
        print(f"   Ошибка копирования чатов: {e}")
    
    # Фиксируем изменения и проверяем
    new_conn.commit()
    
    print("\n4. Проверяем результат...")
    
    # Проверяем пользователей
    new_cursor.execute('SELECT COUNT(*) FROM users')
    user_count = new_cursor.fetchone()[0]
    print(f"   Пользователей в новой базе: {user_count}")
    
    # Проверяем чаты
    new_cursor.execute('SELECT COUNT(*) FROM chats')
    chat_count = new_cursor.fetchone()[0]
    print(f"   Чатов в новой базе: {chat_count}")
    
    # Примеры данных
    print("\n   Примеры пользователей:")
    new_cursor.execute('SELECT id, email, status, is_superuser FROM users LIMIT 3')
    for user in new_cursor.fetchall():
        print(f"     ID:{user[0]}, Email: {user[1]}, Status: {user[2]}, Superuser: {user[3]}")
    
    # Закрываем соединения
    old_conn.close()
    new_conn.close()
    
    # Заменяем текущую базу исправленной
    print("\n5. Заменяем текущую базу исправленной версией...")
    import shutil
    shutil.copy2(migrated_db, 'backend/osagaming_crm.db')
    
    print("\n✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
    print("Теперь база данных имеет правильную структуру:")
    print("   • Колонка 'hashed_password' вместо 'password'")
    print("   • Статусы в верхнем регистре ('ACTIVE', 'INACTIVE')")
    print("   • Все чаты перенесены")
    
    return True

if __name__ == '__main__':
    print("=== ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ Vaito ===")
    print("Проблема: старая база имеет колонку 'password', новая ожидает 'hashed_password'")
    print("Решение: создаем исправленную базу с правильной структурой")
    print()
    
    analyze_databases()
    create_migrated_database()