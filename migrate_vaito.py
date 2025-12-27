#!/usr/bin/env python3
import sqlite3
import os
import datetime

old_db = 'osagaming_crm.db'
new_db = 'backend/osagaming_crm.db'

print('=== MIGRATION FROM OLD VAITO ===')

old_conn = sqlite3.connect(old_db)
old_cursor = old_conn.cursor()

new_conn = sqlite3.connect(new_db)
new_cursor = new_conn.cursor()

print('\\n1. Dropping old tables...')
new_cursor.execute('DROP TABLE IF EXISTS messages')
new_cursor.execute('DROP TABLE IF EXISTS chats')
new_cursor.execute('DROP TABLE IF EXISTS users')

print('2. Creating new tables with correct structure...')
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

new_cursor.execute('''
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
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

new_cursor.execute('''
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        user_id INTEGER,
        content TEXT NOT NULL,
        message_type TEXT NOT NULL DEFAULT 'TEXT',
        is_system BOOLEAN DEFAULT 0,
        is_read BOOLEAN DEFAULT 0,
        is_edited BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats (id)
    )
''')

print('3. Migrating users...')
old_cursor.execute('SELECT * FROM users')
old_users = old_cursor.fetchall()
print(f'   Found {len(old_users)} users')

for user in old_users:
    try:
        user_id = user[0]
        email = user[2]
        hashed_password = user[3]
        first_name = user[13] if len(user) > 13 else user[1]
        last_name = user[14] if len(user) > 14 else None
        role = user[4] if len(user) > 4 else 'user'
        is_active = user[5] if len(user) > 5 else 1
        salary = user[6] if len(user) > 6 else 0
        kpi_score = user[7] if len(user) > 7 else 0
        temp_password = user[8] if len(user) > 8 else None
        password_changed = user[9] if len(user) > 9 else 0
        created_at = user[10] if len(user) > 10 else datetime.datetime.now().isoformat()
        
        is_superuser = 1 if role == 'super_admin' else 0
        status = 'ACTIVE' if is_active == 1 else 'INACTIVE'
        
        new_cursor.execute('''
            INSERT INTO users (id, email, hashed_password, first_name, last_name,
                             status, is_active, is_superuser, kpi_score, salary,
                             temp_password, password_changed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, email, hashed_password, first_name, last_name,
              status, is_active, is_superuser, kpi_score, salary,
              temp_password, password_changed, created_at))
        print(f'   Migrated: {email}')
    except Exception as e:
        print(f'   ERROR: {e}')

print('4. Migrating chats...')
old_cursor.execute('SELECT * FROM chats')
old_chats = old_cursor.fetchall()
print(f'   Found {len(old_chats)} chats')

for chat in old_chats:
    try:
        chat_id = chat[0]
        client_name = chat[1]
        client_phone = chat[2]
        status = chat[3].upper() if chat[3] else 'ACTIVE'
        priority = chat[4].upper() if chat[4] else 'NORMAL'
        created_at = chat[5] if len(chat) > 5 else datetime.datetime.now().isoformat()
        
        new_cursor.execute('''
            INSERT INTO chats (id, user_id, client_name, client_phone,
                             status, priority, created_at, updated_at)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?)
        ''', (chat_id, client_name, client_phone, status, priority, created_at, created_at))
        print(f'   Migrated: {client_name}')
    except Exception as e:
        print(f'   ERROR: {e}')

new_conn.commit()

print('\\n5. Verification...')
new_cursor.execute('SELECT COUNT(*) FROM users')
print(f'   Users in new DB: {new_cursor.fetchone()[0]}')
new_cursor.execute('SELECT COUNT(*) FROM chats')
print(f'   Chats in new DB: {new_cursor.fetchone()[0]}')

old_conn.close()
new_conn.close()

print('\\n=== MIGRATION COMPLETE ===')
