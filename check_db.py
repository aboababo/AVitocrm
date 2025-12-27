import sqlite3

def check_database():
    try:
        conn = sqlite3.connect('backend/osagaming_crm.db')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchall()
        print('Таблицы в БД:', tables)
        
        # Check users table structure
        cursor.execute('PRAGMA table_info(users)')
        columns = cursor.fetchall()
        print('Структура таблицы users:')
        for col in columns:
            print(f'  {col}')
            
        # Check users data
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        print('Пользователи:')
        for user in users:
            print(f'  {user}')
            
        # Check enum values
        cursor.execute("SELECT status FROM users")
        statuses = cursor.fetchall()
        print('Значения статусов в таблице users:', set(statuses))
        
        conn.close()
        return True
    except Exception as e:
        print(f'Ошибка: {e}')
        return False

if __name__ == '__main__':
    check_database()