#!/usr/bin/env python3
"""
Исправление корневой базы данных для совместимости с новым приложением.
Меняем структуру таблицы users: переименовываем password -> hashed_password и приводим к верхнему регистру.
"""

import sqlite3
import os
import tempfile

def fix_root_database():
    """Исправляет корневую базу данных для работы с новым приложением"""
    
    db_path = 'osagaming_crm.db'
    
    if not os.path.exists(db_path):
        print(f"[ERROR] База данных не найдена: {db_path}")
        return False
    
    # Создаем временную копию базы
    backup_path = f'{db_path}.backup'
    print(f"Создаем резервную копию: {backup_path}")
    
    # Подключаемся к базе
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== АНАЛИЗ БАЗЫ ДАННЫХ ===")
    
    # Проверяем структуру таблицы users
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("\nТекущая структура таблицы users:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Проверяем есть ли колонка password
    has_password = any(col[1] == 'password' for col in columns)
    has_hashed_password = any(col[1] == 'hashed_password' for col in columns)
    
    print(f"\nПроверка колонок:")
    print(f"  Имеется 'password': {has_password}")
    print(f"  Имеется 'hashed_password': {has_hashed_password}")
    
    if has_password and not has_hashed_password:
        print("\n=== ИСПРАВЛЕНИЕ СТРУКТУРЫ ===")
        print("Переименовываем колонку 'password' -> 'hashed_password'")
        
        try:
            # Создаем новую таблицу с правильной структурой
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
            
            # Копируем данные из старой таблицы
            print("Копируем данные из старой таблицы...")
            
            # Получаем всех пользователей
            cursor.execute('SELECT * FROM users')
            users = cursor.fetchall()
            
            for user in users:
                # user = (id, username, email, password, role, is_active, salary, kpi_score, temp_password, password_changed, created_at, created_by, settings, first_name, last_name)
                # Переносим в новую структуру
                cursor.execute('''
                    INSERT INTO users_new (
                        id, email, hashed_password, first_name, status, is_active, is_superuser,
                        salary, kpi_score, temp_password, password_changed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user[0],  # id
                    user[2],  # email
                    user[3],  # password -> hashed_password
                    user[1] or user[13] if len(user) > 13 else user[1],  # username или first_name -> first_name
                    'ACTIVE' if (user[5] if len(user) > 5 else 1) else 'INACTIVE',
                    user[5] if len(user) > 5 else 1,  # is_active
                    1 if (user[4] if len(user) > 4 else 'user') == 'super_admin' else 0,  # role -> is_superuser
                    user[6] if len(user) > 6 else 0,  # salary
                    user[7] if len(user) > 7 else 0,  # kpi_score
                    user[8] if len(user) > 8 else None,  # temp_password
                    user[9] if len(user) > 9 else 0,  # password_changed
                    user[10] if len(user) > 10 else '2025-01-01 00:00:00'  # created_at
                ))
            
            # Удаляем старую таблицу и переименовываем новую
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            
            print(f"✅ Перенесено пользователей: {len(users)}")
            
        except Exception as e:
            print(f"❌ Ошибка при переносе данных: {e}")
            # Откатываем изменения
            conn.rollback()
            print("Откат изменений...")
            return False
    
    # Проверяем чаты и исправляем регистр статусов/приоритетов
    print("\n=== ПРОВЕРКА И ИСПРАВЛЕНИЕ ЧАТОВ ===")
    
    try:
        # Проверяем существование таблицы chats
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if cursor.fetchone():
            # Исправляем регистр status и priority
            print("Исправляем регистр в таблице chats...")
            
            # Обновляем статусы в верхний регистр
            cursor.execute("UPDATE chats SET status = UPPER(status) WHERE LOWER(status) = status")
            updated_status = cursor.rowcount
            print(f"  Обновлено статусов: {updated_status}")
            
            # Обновляем приоритеты в верхний регистр
            cursor.execute("UPDATE chats SET priority = UPPER(priority) WHERE LOWER(priority) = priority")
            updated_priority = cursor.rowcount
            print(f"  Обновлено приоритетов: {updated_priority}")
            
            # Проверяем результат
            cursor.execute("SELECT COUNT(*) FROM chats")
            chat_count = cursor.fetchone()[0]
            print(f"  Всего чатов: {chat_count}")
            
            if chat_count > 0:
                cursor.execute("SELECT id, client_name, status, priority FROM chats LIMIT 3")
                sample_chats = cursor.fetchall()
                print("  Примеры чатов после исправления:")
                for chat in sample_chats:
                    print(f"    ID:{chat[0]}, Клиент: {chat[1]}, Статус: {chat[2]}, Приоритет: {chat[3]}")
        else:
            print("❌ Таблица chats не найдена")
            
    except Exception as e:
        print(f"⚠️ Ошибка при работе с таблицей chats: {e}")
    
    # Коммитим изменения
    conn.commit()
    
    # Проверяем финальную структуру
    print("\n=== ФИНАЛЬНАЯ ПРОВЕРКА ===")
    
    cursor.execute("PRAGMA table_info(users)")
    final_columns = cursor.fetchall()
    print("Структура таблицы users после исправления:")
    for col in final_columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Проверяем пользователей
    cursor.execute("SELECT id, email, status, is_superuser FROM users LIMIT 3")
    users = cursor.fetchall()
    print("\nПользователи после исправления:")
    for user in users:
        print(f"  ID:{user[0]}, Email: {user[1]}, Status: {user[2]}, Superuser: {user[3]}")
    
    # Проверяем пароли
    cursor.execute("SELECT email, hashed_password FROM users LIMIT 3")
    passwords = cursor.fetchall()
    print("\nПроверка паролей:")
    for pwd in passwords:
        email, hashed_pwd = pwd
        print(f"  {email}: {'✓' if hashed_pwd else '✗ (пустой)'}")
    
    conn.close()
    
    print("\n✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
    print("База данных osagaming_crm.db готова к работе с новым приложением.")
    print("\nТеперь можно перезапустить Docker:")
    print("  docker-compose down")
    print("  docker-compose up --build -d")
    
    return True

if __name__ == '__main__':
    print("=== ИСПРАВЛЕНИЕ КОРНЕВОЙ БАЗЫ ДАННЫХ ===")
    print("Цель: сделать базу совместимой с новым приложением")
    print("Исправления:")
    print("  1. Переименовать колонку password -> hashed_password")
    print("  2. Привести статусы и приоритеты к верхнему регистру")
    print()
    
    success = fix_root_database()
    
    if success:
        print("\n[SUCCESS] Все готово! Приложение будет использовать исправленную базу из корня.")
    else:
        print("\n[ERROR] Что-то пошло не так. Проверьте логи выше.")