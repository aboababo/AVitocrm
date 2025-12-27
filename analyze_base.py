#!/usr/bin/env python3
"""
Анализ базы base.db
"""

import sqlite3

def analyze_base_db():
    """Анализирует структуру и данные в base.db"""
    
    db_path = 'base.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print('=== АНАЛИЗ БАЗЫ ДАННЫХ BASE.DB ===')
    
    # 1. Получаем все таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f'\nВсего таблиц: {len(tables)}')
    
    for table in tables:
        table_name = table[0]
        print(f'\n--- ТАБЛИЦА: {table_name} ---')
        
        # Структура таблицы
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = cursor.fetchall()
        
        print('Колонки:')
        for col in columns:
            print(f'  {col[1]} ({col[2]}) - default: {col[4]}')
        
        # Количество записей
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'Записей: {count}')
        
        # Пример данных (первые 3 записи)
        if count > 0 and count < 1000:  # Не выводим примеры если слишком много данных
            cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
            rows = cursor.fetchall()
            print('Примеры данных (первые 3 записи):')
            for i, row in enumerate(rows, 1):
                print(f'  Запись {i}: {row}')
    
    # Особое внимание на таблицы users, chats, messages
    print('\n\n=== ПРОВЕРКА КЛЮЧЕВЫХ ТАБЛИЦ ===')
    
    key_tables = ['users', 'chats', 'messages']
    
    for table_name in key_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if cursor.fetchone():
            print(f'\n--- {table_name.upper()} ---')
            
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'Записей: {count}')
            
            # Проверяем структуру
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            print('Колонки:')
            for col in columns:
                print(f'  {col[1]} ({col[2]})')
    
    conn.close()

if __name__ == '__main__':
    analyze_base_db()