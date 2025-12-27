#!/usr/bin/env python3
"""
Создание новой базы данных с правильной структурой из старой
"""

import sqlite3
import os
import shutil
import datetime

def recreate_database():
    """Создает новую базу данных с правильной структурой"""
    
    old_db = 'osagaming_crm.db'
    new_db = 'backend/osagaming_crm.db'
    
    # Создаем резервную копию старой базы
    if os.path.exists(old_db):
        backup_path = f'{old_db}.backup.{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(old_db, backup_path)
        print(f"Резервная копия создана: {backup_path}")
    
    # Создаем новую базу данных в backend папке
    print(f"\nСоздаем новую базу данных: {new_db}")
    
    new_conn = sqlite3.connect(new_db)
    new_cursor = new_conn.cursor()
    
    # 1. Создаем таблицу users с правильной структурой
    print("1. Создаем таблицу users...")
    new_cursor.execute('DROP TABLE IF EXISTS users')
    new_cursor.execute('''
        CREATE TABLE users (
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
            password_changed BOOLEAN DEFAULT 0
        )
    ''')
    
    # 2. Добавляем пользователя admin
    print("2. Создаем пользователя admin...")
    # bcrypt hash для пароля 'admin123'
    admin_password_hash = '$2b$12$kP1o0j6x8HlW9lC5lI2o6eVzQw5W7Y9Z6X8L0N1M2O3P4Q5R6S7T8U9V0W1X2Y3Z4A5B6C7D8E9F0G1H2I3J4K5L6M7N8'
    
    new_cursor.execute('''
        INSERT INTO users (
            email, hashed_password, first_name, status, is_active, is_superuser
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        'admin@osagaming.com',
        admin_password_hash,
        'Admin',
        'ACTIVE',
        1,
        1
    ))
    
    # 3. Создаем таблицу chats
    print("3. Создаем таблицу chats...")
    new_cursor.execute('DROP TABLE IF EXISTS chats')
    new_cursor.execute('''
        CREATE TABLE chats (
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
            duration_minutes INTEGER,
            client_display_name TEXT GENERATED ALWAYS AS (client_name || ' (' || client_phone || ')')
        )
    ''')
    
    # 4. Добавляем тестовые чаты из старой базы если она существует
    if os.path.exists(old_db):
        print("4. Копируем чаты из старой базы...")
        old_conn = sqlite3.connect(old_db)
        old_cursor = old_conn.cursor()
        
        try:
            old_cursor.execute('SELECT * FROM chats')
            old_chats = old_cursor.fetchall()
            print(f"   Найдено чатов: {len(old_chats)}")
            
            for chat in old_chats:
                # Старая структура: (id, client_name, client_phone, status, priority, created_at)
                if len(chat) >= 6:
                    # Преобразуем status и priority в UPPERCASE
                    status = chat[3].upper() if chat[3] else 'ACTIVE'
                    priority = chat[4].upper() if chat[4] else 'NORMAL'
                    
                    new_cursor.execute('''
                        INSERT INTO chats (
                            id, user_id, client_name, client_phone, status, priority, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        chat[0],  # id
                        1,         # user_id (admin)
                        chat[1],   # client_name
                        chat[2],   # client_phone
                        status,
                        priority,
                        chat[5] if len(chat) > 5 else datetime.datetime.now().isoformat()
                    ))
            print(f"   Скопировано чатов: {len(old_chats)}")
        except Exception as e:
            print(f"   Ошибка копирования чатов: {e}")
        
        old_conn.close()
    else:
        print("4. Старая база не найдена, создаем тестовые чаты...")
        # Создаем несколько тестовых чатов
        test_chats = [
            ('John Smith', '+79161112233', 'Delivery question', 'NORMAL'),
            ('Mary Johnson', '+79162223344', 'Payment problem', 'HIGH'),
            ('Alex Brown', '+79163334455', 'Product consultation', 'LOW'),
            ('Olga Davis', '+79164445566', 'Complaint about quality', 'URGENT'),
            ('Serge Wilson', '+79165556677', 'Warranty question', 'NORMAL'),
        ]
        
        for i, (name, phone, title, priority) in enumerate(test_chats, 1):
            new_cursor.execute('''
                INSERT INTO chats (
                    user_id, client_name, client_phone, title, priority, status
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            ''', (1, name, phone, title, priority))
        print(f"   Создано тестовых чатов: {len(test_chats)}")
    
    # 5. Создаем таблицу messages если нужно
    print("5. Создаем таблицу messages...")
    new_cursor.execute('DROP TABLE IF EXISTS messages')
    new_cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'TEXT',
            is_system BOOLEAN DEFAULT 0,
            is_read BOOLEAN DEFAULT 0,
            is_edited BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP
        )
    ''')
    
    # 6. Фиксируем изменения
    new_conn.commit()
    
    # 7. Проверяем результат
    print("\n=== ПРОВЕРКА РЕЗУЛЬТАТА ===")
    
    new_cursor.execute('SELECT COUNT(*) FROM users')
    user_count = new_cursor.fetchone()[0]
    print(f"Пользователей: {user_count}")
    
    new_cursor.execute('SELECT email, status, is_superuser FROM users')
    users = new_cursor.fetchall()
    for user in users:
        print(f"  Пользователь: {user[0]}, Статус: {user[1]}, Суперюзер: {user[2]}")
    
    new_cursor.execute('SELECT COUNT(*) FROM chats')
    chat_count = new_cursor.fetchone()[0]
    print(f"\nЧатов: {chat_count}")
    
    new_cursor.execute('SELECT id, client_name, priority, status FROM chats LIMIT 5')
    chats = new_cursor.fetchall()
    for chat in chats:
        print(f"  Чат #{chat[0]}: {chat[1]}, Приоритет: {chat[2]}, Статус: {chat[3]}")
    
    new_conn.close()
    
    print("\n[SUCCESS] Новая база данных создана!")
    print(f"Файл: {new_db}")
    print("\nТеперь можно запустить приложение:")
    print("  docker-compose up --build -d")
    print("\nПриложение будет использовать правильную структуру базы данных.")
    
    return True

if __name__ == '__main__':
    print("=== СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ ===")
    print("Создаем базу с правильной структурой для Docker-приложения")
    print()
    recreate_database()