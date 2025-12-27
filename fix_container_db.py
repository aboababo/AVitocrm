import sqlite3

def fix_database():
    """Исправляет базу данных внутри контейнера"""
    
    db_path = '/app/osagaming_crm.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print('=== FIXING DATABASE IN CONTAINER ===')
    
    # 1. Удаляем users_new если она есть
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_new'")
    if cursor.fetchone():
        print('1. Dropping old users_new table...')
        cursor.execute('DROP TABLE users_new')
        print('   users_new dropped')
    else:
        print('1. users_new table does not exist - OK')
    
    # 2. Создаем новую таблицу users_new
    print('2. Creating new users_new table...')
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
    print('   users_new created')
    
    # 3. Копируем данные из users в users_new
    print('3. Copying data from users to users_new...')
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    print(f'   Found {len(users)} users')
    
    for user in users:
        # user: (id, username, email, password, role, is_active, salary, kpi_score, temp_password, password_changed, created_at, created_by, settings, first_name, last_name)
        cursor.execute('''
            INSERT INTO users_new (id, email, hashed_password, first_name, status, is_active, is_superuser,
                                   salary, kpi_score, temp_password, password_changed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user[0],    # id
            user[2],    # email
            user[3],    # password -> hashed_password
            user[1] or user[13] if len(user) > 13 else user[1],  # username или first_name
            'ACTIVE' if (user[5] if len(user) > 5 else 1) else 'INACTIVE',
            user[5] if len(user) > 5 else 1,
            1 if (user[4] if len(user) > 4 else 'user') == 'super_admin' else 0,
            user[6] if len(user) > 6 else 0,
            user[7] if len(user) > 7 else 0,
            user[8] if len(user) > 8 else None,
            user[9] if len(user) > 9 else 0,
            user[10] if len(user) > 10 else '2025-01-01 00:00:00'
        ))
    
    print(f'   Copied {len(users)} users')
    
    # 4. Заменяем таблицу
    print('4. Replacing users table...')
    cursor.execute('DROP TABLE users')
    cursor.execute('ALTER TABLE users_new RENAME TO users')
    print('   users table replaced')
    
    # 5. Исправляем чаты
    print('5. Fixing chats table...')
    cursor.execute('UPDATE chats SET status = UPPER(status) WHERE LOWER(status) = status')
    updated_status = cursor.rowcount
    print(f'   Updated {updated_status} statuses')
    
    cursor.execute('UPDATE chats SET priority = UPPER(priority) WHERE LOWER(priority) = priority')
    updated_priority = cursor.rowcount
    print(f'   Updated {updated_priority} priorities')
    
    # 6. Коммитим и проверяем
    conn.commit()
    
    print('6. Verifying results...')
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    print(f'   Total users: {user_count}')
    
    cursor.execute('SELECT email, status, is_superuser FROM users')
    users = cursor.fetchall()
    print('   Users in database:')
    for user in users:
        print(f'     {user[0]}, status={user[1]}, super={user[2]}')
    
    conn.close()
    
    print('[SUCCESS] Database fixed in container!')

if __name__ == '__main__':
    fix_database()