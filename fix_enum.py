#!/usr/bin/env python3
"""
Скрипт для исправления проблем с enum в базе данных.
Проблема: в базе данных значения хранятся как 'active', но миграция ожидает 'ACTIVE'.
"""

import sqlite3
import subprocess
import sys
import os

def fix_database_enum():
    """Исправляет проблемы с enum в базе данных"""
    
    db_path = 'backend/osagaming_crm.db'
    
    if not os.path.exists(db_path):
        print(f'База данных не найдена: {db_path}')
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print('Проверка текущих данных...')
        
        # Проверяем текущие статусы
        cursor.execute('SELECT status FROM users')
        statuses = cursor.fetchall()
        print(f'Текущие статусы: {set(statuses)}')
        
        # Проверяем тип колонки
        cursor.execute('PRAGMA table_info(users)')
        columns = cursor.fetchall()
        status_col = None
        for col in columns:
            if col[1] == 'status':
                status_col = col
                break
        
        print(f'Информация о колонке status: {status_col}')
        
        if status_col and status_col[2] == 'VARCHAR(9)':
            print('Колонка имеет тип VARCHAR, нужно преобразовать к новому enum')
            
            # Обновляем данные к новому формату
            print('Обновление статусов пользователей...')
            
            # Сначала проверим, какие статусы есть
            cursor.execute('SELECT DISTINCT status FROM users')
            distinct_statuses = cursor.fetchall()
            print(f'Различные статусы: {distinct_statuses}')
            
            # Обновляем 'active' -> 'ACTIVE'
            cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE status = 'active'")
            
            # Проверяем другие возможные статусы
            cursor.execute("SELECT COUNT(*) FROM users WHERE status NOT IN ('ACTIVE', 'INACTIVE', 'BLOCKED')")
            other_statuses_count = cursor.fetchone()[0]
            
            if other_statuses_count > 0:
                print(f'Найдены {other_statuses_count} записей с нестандартными статусами')
                cursor.execute("SELECT id, status FROM users WHERE status NOT IN ('ACTIVE', 'INACTIVE', 'BLOCKED')")
                for user_id, status in cursor.fetchall():
                    print(f'Пользователь {user_id}: статус "{status}" -> установлен "ACTIVE"')
                    cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE id = ?", (user_id,))
            
            conn.commit()
            
            # Проверяем результат
            cursor.execute('SELECT status FROM users')
            new_statuses = cursor.fetchall()
            print(f'Новые статусы после обновления: {set(new_statuses)}')
            
        else:
            print('Колонка уже имеет другой тип или не найдена')
        
        conn.close()
        print('✅ База данных обновлена успешно')
        return True
        
    except Exception as e:
        print(f'❌ Ошибка при обновлении базы данных: {e}')
        import traceback
        traceback.print_exc()
        return False

def run_alembic_migrations():
    """Запускает миграции alembic"""
    print('\nЗапуск миграций alembic...')
    
    try:
        # Используем правильный путь к алембику
        subprocess.run(
            ['python', '-m', 'alembic', 'upgrade', 'head'],
            cwd='backend',
            check=True
        )
        print('✅ Миграции alembic выполнены успешно')
        return True
    except subprocess.CalledProcessError as e:
        print(f'❌ Ошибка при выполнении миграций alembic: {e}')
        return False

def main():
    print('=== Исправление проблем с enum в базе данных ===')
    
    if not fix_database_enum():
        print('Не удалось исправить базу данных')
        sys.exit(1)
    
    # Запускаем миграции для применения изменений к схеме
    if not run_alembic_migrations():
        print('Не удалось выполнить миграции')
        sys.exit(1)
    
    print('\n✅ Все операции выполнены успешно!')
    print('Теперь можно перезапустить приложение:')
    print('  docker-compose down')
    print('  docker-compose up --build')

if __name__ == '__main__':
    main()