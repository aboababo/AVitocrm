#!/usr/bin/env python3
"""
Полная миграция из base.db в backend/osagaming_crm.db
1. Удаляет все старые базы кроме base.db
2. Создает новую базу с правильной структурой
3. Переносит все данные
"""

import sqlite3
import os
import shutil

def delete_old_databases():
    """Удаляет все базы кроме base.db"""
    
    print('=== УДАЛЕНИЕ СТАРЫХ БАЗ ДАННЫХ ===')
    
    databases_to_delete = [
        'osagaming_crm.db',
        'crm.db',
        'temp_users.db',
        'backend/crm.db',
        'backend/migrated_crm.db',
        'backend/osagaming_crm.db'
    ]
    
    deleted_count = 0
    for db_path in databases_to_delete:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f'Deleted: {db_path}')
                deleted_count += 1
            except Exception as e:
                print(f'Error deleting {db_path}: {e}')
    
    print(f'Deleted {deleted_count} database files')

def create_new_database():
    """Создает новую базу с правильной структурой для backend"""
    
    print('\n=== СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ ===')
    
    db_path = 'backend/osagaming_crm.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Таблица users (новая структура)
    cursor.execute('''
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
    print('Created table: users')
    
    # Таблица chats (новая структура)
    cursor.execute('''
        CREATE TABLE chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shop_id INTEGER,
            chat_id TEXT,
            external_id TEXT,
            customer_id TEXT,
            client_name TEXT,
            client_phone TEXT,
            client_email TEXT,
            client_location TEXT,
            product_url TEXT,
            listing_id TEXT,
            listing_data TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            priority TEXT NOT NULL DEFAULT 'NORMAL',
            title TEXT,
            description TEXT,
            tags TEXT,
            message_count INTEGER DEFAULT 0,
            unread_count INTEGER DEFAULT 0,
            response_timer INTEGER DEFAULT 0,
            last_message TEXT,
            last_activity_at TIMESTAMP,
            last_message_at TIMESTAMP,
            assigned_manager_id INTEGER,
            assigned_manager_name TEXT,
            is_in_pool BOOLEAN DEFAULT 1,
            last_assigned_at TIMESTAMP,
            last_released_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            duration_minutes INTEGER
        )
    ''')
    print('Created table: chats')
    
    # Таблица messages (новая структура)
    cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER,
            external_id TEXT,
            content TEXT NOT NULL,
            message_type TEXT NOT NULL DEFAULT 'TEXT',
            is_system BOOLEAN DEFAULT 0,
            is_read BOOLEAN DEFAULT 0,
            is_edited BOOLEAN DEFAULT 0,
            message_status TEXT DEFAULT 'sent',
            sender_type TEXT,
            sender_name TEXT,
            attachment_url TEXT,
            attachment_name TEXT,
            attachment_size INTEGER,
            extra_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print('Created table: messages')
    
    conn.commit()
    conn.close()
    
    print(f'New database created: {db_path}')
    
    return db_path

def migrate_data():
    """Переносит данные из base.db в новую базу"""
    
    print('\n=== ПЕРЕНОС ДАННЫХ ИЗ BASE.DB ===')
    
    old_db = 'base.db'
    new_db = 'backend/osagaming_crm.db'
    
    old_conn = sqlite3.connect(old_db)
    new_conn = sqlite3.connect(new_db)
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # 1. Перенос пользователей
    print('\n1. Перенос users...')
    old_cursor.execute('SELECT * FROM users')
    users = old_cursor.fetchall()
    
    for user in users:
        # Маппинг данных из старой структуры в новую
        # old: [id, username, email, password, role, is_active, salary, kpi_score, 
        #       temp_password, password_changed, created_at, created_by, settings, first_name, last_name]
        
        hashed_password = user[3] if user[3] else 'password'
        role = user[4] if len(user) > 4 else 'manager'
        is_superuser = 1 if role == 'super_admin' else 0
        is_active = user[5] if len(user) > 5 else 1
        
        status = 'ACTIVE' if is_active else 'INACTIVE'
        
        new_cursor.execute('''
            INSERT INTO users (
                id, email, hashed_password, first_name, last_name,
                status, is_active, is_superuser, kpi_score, salary,
                temp_password, password_changed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user[0],  # id
            user[2],  # email
            hashed_password,
            user[13] if len(user) > 13 else user[1],  # first_name (или username)
            user[14] if len(user) > 14 else None,  # last_name
            status,
            is_active,
            is_superuser,
            user[7] if len(user) > 7 else 0,  # kpi_score
            user[6] if len(user) > 6 else 0,  # salary
            user[8] if len(user) > 8 else None,  # temp_password
            user[9] if len(user) > 9 else 0,  # password_changed
            user[10] if len(user) > 10 else None  # created_at
        ))
    
    print(f'   Transferred {len(users)} users')
    
    # 2. Перенос avito_chats (основные чаты)
    print('\n2. Перенос avito_chats...')
    old_cursor.execute('SELECT * FROM avito_chats')
    avito_chats = old_cursor.fetchall()
    
    for chat in avito_chats:
        # old: [id, shop_id, chat_id, client_name, client_phone, product_url,
        #       last_message, priority, status, unread_count, response_timer,
        #       customer_id, assigned_manager_id, created_at, updated_at, listing_data]
        
        # Преобразуем приоритет
        old_priority = chat[7] if len(chat) > 7 else 'normal'
        priority_map = {
            'new': 'URGENT',
            'urgent': 'URGENT',
            'high': 'HIGH',
            'normal': 'NORMAL',
            'low': 'LOW'
        }
        new_priority = priority_map.get(old_priority.lower(), 'NORMAL')
        
        # Преобразуем статус
        old_status = chat[8] if len(chat) > 8 else 'active'
        status_map = {
            'active': 'ACTIVE',
            'pending': 'PENDING',
            'closed': 'CLOSED',
            'archived': 'ARCHIVED'
        }
        new_status = status_map.get(old_status.lower(), 'ACTIVE')
        
        # Для user_id используем assigned_manager_id или 1 (admin)
        user_id = chat[12] if len(chat) > 12 and chat[12] else 1
        
        new_cursor.execute('''
            INSERT INTO chats (
                id, user_id, shop_id, chat_id, customer_id,
                client_name, client_phone, product_url,
                status, priority, unread_count, response_timer,
                assigned_manager_id, created_at, updated_at, listing_data,
                is_in_pool, last_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        ''', (
            chat[0],  # id
            user_id,
            chat[1] if len(chat) > 1 else None,  # shop_id
            chat[2] if len(chat) > 2 else None,  # chat_id
            chat[13] if len(chat) > 13 else None,  # customer_id
            chat[3] if len(chat) > 3 else None,  # client_name
            chat[4] if len(chat) > 4 else None,  # client_phone
            chat[5] if len(chat) > 5 else None,  # product_url
            new_status,
            new_priority,
            chat[9] if len(chat) > 9 else 0,  # unread_count
            chat[10] if len(chat) > 10 else 0,  # response_timer
            chat[12] if len(chat) > 12 else None,  # assigned_manager_id
            chat[14] if len(chat) > 14 else None,  # created_at
            chat[15] if len(chat) > 15 else None,  # updated_at
            chat[16] if len(chat) > 16 else None,  # listing_data
            chat[6] if len(chat) > 6 else None  # last_message
        ))
    
    print(f'   Transferred {len(avito_chats)} avito_chats')
    
    # 3. Перенос avito_messages
    print('\n3. Перенос avito_messages...')
    old_cursor.execute('SELECT * FROM avito_messages')
    avito_messages = old_cursor.fetchall()
    
    for msg in avito_messages:
        # old: [id, chat_id, message_text, message_type, sender_name,
        #       manager_id, is_read, timestamp]
        
        new_cursor.execute('''
            INSERT INTO messages (
                id, chat_id, user_id, content, message_type,
                is_read, sender_name, timestamp, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            msg[0],  # id
            msg[1] if len(msg) > 1 else None,  # chat_id
            msg[5] if len(msg) > 5 else None,  # manager_id (user_id)
            msg[2] if len(msg) > 2 else '',  # message_text
            msg[3] if len(msg) > 3 else 'TEXT',  # message_type
            msg[6] if len(msg) > 6 else 0,  # is_read
            msg[4] if len(msg) > 4 else None,  # sender_name
            msg[7] if len(msg) > 7 else None,  # timestamp
            msg[7] if len(msg) > 7 else None,  # created_at
            msg[7] if len(msg) > 7 else None  # updated_at
        ))
    
    print(f'   Transferred {len(avito_messages)} avito_messages')
    
    # Обновляем счетчики сообщений в чатах
    print('\n4. Обновление счетчиков сообщений...')
    new_cursor.execute('''
        UPDATE chats SET message_count = (
            SELECT COUNT(*) FROM messages WHERE messages.chat_id = chats.id
        )
    ''')
    
    new_conn.commit()
    new_conn.close()
    old_conn.close()
    
    print('\n=== РЕЗУЛЬТАТ МИГРАЦИИ ===')
    print(f'Users: {len(users)}')
    print(f'Avito Chats: {len(avito_chats)}')
    print(f'Avito Messages: {len(avito_messages)}')
    
    return True

if __name__ == '__main__':
    print('=== МАССОВАЯ МИГРАЦИЯ БАЗЫ ДАННЫХ ===')
    print('1. Удаление старых баз')
    print('2. Создание новой базы с правильной структурой')
    print('3. Перенос всех данных из base.db')
    print()
    
    try:
        delete_old_databases()
        create_new_database()
        migrate_data()
        
        print('\n✅ Миграция завершена успешно!')
        print('====================================')
        print('Теперь перезапустите Docker:')
        print('  docker-compose down')
        print('  docker-compose up --build -d')
        print('====================================')
        
    except Exception as e:
        print(f'❌ Ошибка миграции: {e}')
        import traceback
        traceback.print_exc()