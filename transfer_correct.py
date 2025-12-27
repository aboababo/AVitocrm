#!/usr/bin/env python3
"""
Корректный перенос данных с учетом структуры таблиц
"""

import sqlite3
import os

def check_table_structure(conn, table_name):
    """Проверяет структуру таблицы"""
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    print(f'Структура таблицы {table_name}:')
    for col in columns:
        print(f'  {col[1]}: {col[2]} (default: {col[4]})')
    return columns

def transfer_data_correctly():
    """Перенос данных с учетом структуры таблиц"""
    
    old_db = 'osagaming_crm.db'
    new_db = 'backend/osagaming_crm.db'
    
    if not os.path.exists(old_db):
        print(f'❌ Старая база не найдена: {old_db}')
        return False
    
    if not os.path.exists(new_db):
        print(f'❌ Новая база не найдена: {new_db}')
        return False
    
    try:
        # Подключаемся к базам
        old_conn = sqlite3.connect(old_db)
        new_conn = sqlite3.connect(new_db)
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        print('=== АНАЛИЗ СТРУКТУРЫ БАЗ ДАННЫХ ===')
        
        # 1. Проверяем структуру таблицы users в обеих базах
        print('\n1. Таблица USERS:')
        old_users_cols = check_table_structure(old_conn, 'users')
        new_users_cols = check_table_structure(new_conn, 'users')
        
        print(f'\n   Старая база: {len(old_users_cols)} колонок')
        print(f'   Новая база:  {len(new_users_cols)} колонок')
        
        # 2. Проверяем структуру таблицы chats
        print('\n2. Таблица CHATS:')
        old_chats_cols = check_table_structure(old_conn, 'chats')
        new_chats_cols = check_table_structure(new_conn, 'chats')
        
        print(f'\n   Старая база: {len(old_chats_cols)} колонок')
        print(f'   Новая база:  {len(new_chats_cols)} колонок')
        
        # 3. Очищаем новые таблицы
        print('\n3. Очистка новых таблиц...')
        try:
            new_cursor.execute('DELETE FROM messages')
            print('   ✅ Таблица messages очищена')
        except:
            print('   ⚠️  Таблица messages не существует или ошибка очистки')
        
        new_cursor.execute('DELETE FROM chats')
        print('   ✅ Таблица chats очищена')
        
        new_cursor.execute('DELETE FROM users')
        print('   ✅ Таблица users очищена')
        
        # 4. Копируем пользователей (только совпадающие колонки)
        print('\n4. Копирование пользователей...')
        old_cursor.execute('SELECT * FROM users')
        old_users = old_cursor.fetchall()
        
        for user_data in old_users:
            # Для каждой записи пользователя
            # Создаем словарь колонок для явного указания
            col_names = [col[1] for col in old_users_cols]
            user_dict = dict(zip(col_names, user_data))
            
            # Создаем список значений для новой таблицы
            # Берем только те колонки, которые есть в новой таблице
            new_values = []
            for new_col in new_users_cols:
                col_name = new_col[1]
                if col_name in user_dict:
                    new_values.append(user_dict[col_name])
                else:
                    # Значение по умолчанию
                    new_values.append(None)
            
            # Вставляем данные
            placeholders = ','.join(['?' for _ in new_values])
            new_cursor.execute(f'INSERT INTO users VALUES ({placeholders})', new_values)
        
        print(f'   ✅ Скопировано пользователей: {len(old_users)}')
        
        # 5. Копируем чаты
        print('\n5. Копирование чатов...')
        old_cursor.execute('SELECT * FROM chats')
        old_chats = old_cursor.fetchall()
        
        for chat_data in old_chats:
            col_names = [col[1] for col in old_chats_cols]
            chat_dict = dict(zip(col_names, chat_data))
            
            new_values = []
            for new_col in new_chats_cols:
                col_name = new_col[1]
                if col_name in chat_dict:
                    new_values.append(chat_dict[col_name])
                else:
                    new_values.append(None)
            
            placeholders = ','.join(['?' for _ in new_values])
            new_cursor.execute(f'INSERT INTO chats VALUES ({placeholders})', new_values)
        
        print(f'   ✅ Скопировано чатов: {len(old_chats)}')
        
        # 6. Фиксируем изменения
        new_conn.commit()
        
        # 7. Проверяем результат
        print('\n=== ИТОГОВАЯ ПРОВЕРКА ===')
        
        new_cursor.execute('SELECT COUNT(*) FROM users')
        new_user_count = new_cursor.fetchone()[0]
        print(f'Пользователей в новой базе: {new_user_count}')
        
        new_cursor.execute('SELECT COUNT(*) FROM chats')
        new_chat_count = new_cursor.fetchone()[0]
        print(f'Чатов в новой базе: {new_chat_count}')
        
        # Примеры чатов
        print('\nПримеры чатов (первых 5):')
        new_cursor.execute('SELECT id, client_name, title, priority, status FROM chats ORDER BY id LIMIT 5')
        sample = new_cursor.fetchall()
        for chat in sample:
            print(f'  ID:{chat[0]}, {chat[1]}: {chat[2]}')
        
        # Закрываем соединения
        old_conn.close()
        new_conn.close()
        
        print('\n✅ ПЕРЕНОС ДАННЫХ ЗАВЕРШЕН УСПЕШНО!')
        print('Теперь в Docker-контейнере будут старые чаты из Vaito.')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка при переносе данных: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('=== КОРРЕКТНЫЙ ПЕРЕНОС ДАННЫХ ИЗ Vaito ===')
    print('Учитывает разную структуру таблиц')
    print()
    transfer_data_correctly()