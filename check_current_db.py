import sqlite3
import os

db_path = 'backend/osagaming_crm.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print('=== ПРОВЕРКА БАЗЫ ДАННЫХ ===')
    
    # Check all tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')
    tables = cursor.fetchall()
    print('Таблицы в базе:')
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
        count = cursor.fetchone()[0]
        print(f'  {table[0]}: {count} записей')
    
    # Check chats data more thoroughly
    try:
        cursor.execute('SELECT id, client_name, title, priority, status FROM chats ORDER BY id LIMIT 10')
        chats = cursor.fetchall()
        print(f'\nПримеры чатов ({len(chats)} из общего числа):')
        for chat in chats:
            print(f'  ID:{chat[0]}, Имя: "{chat[1]}", Тема: "{chat[2]}", Приоритет: "{chat[3]}", Статус: "{chat[4]}"')
            
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM chats')
        total_chats = cursor.fetchone()[0]
        print(f'\nВсего чатов в базе: {total_chats}')
    except Exception as e:
        print(f'Ошибка чтения чатов: {e}')
    
    # Check users table
    try:
        cursor.execute('SELECT id, email, status FROM users ORDER BY id')
        users = cursor.fetchall()
        print(f'\nПользователи ({len(users)} всего):')
        for user in users:
            print(f'  ID:{user[0]}, Email: {user[1]}, Статус: "{user[2]}"')
    except Exception as e:
        print(f'Ошибка чтения пользователей: {e}')
    
    # Check messages
    try:
        cursor.execute('SELECT COUNT(*) FROM messages')
        message_count = cursor.fetchone()[0]
        print(f'\nСообщений в базе: {message_count}')
    except:
        print(f'\nСообщений в базе: 0 (таблица messages может не существовать)')
    
    conn.close()
    
    print('\n=== ПРОВЕРКА DOCKER-КОНТЕЙНЕРА ===')
    print('Приложение использует базу данных: backend/osagaming_crm.db')
    print('Если эта база пуста, значит Docker-контейнер использует свою собственную базу')
    print('\nРешение:')
    print('1. Скопируйте старые данные из корневой базы (osagaming_crm.db в корне проекта)')
    print('2. Или переключитесь на использование корневой базы в docker-compose.yml')
else:
    print(f'База данных не найдена: {db_path}')