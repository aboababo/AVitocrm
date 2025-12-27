#!/usr/bin/env python3
"""
Перенос данных из старой базы в новую
"""

import sqlite3
import os

def transfer_data():
    """Переносит данные из старой базы в новую"""
    
    old_db = 'osagaming_crm.db'  # Старая база в корне
    new_db = 'backend/osagaming_crm.db'  # Новая база для Docker
    
    if not os.path.exists(old_db):
        print(f'❌ Старая база не найдена: {old_db}')
        return False
    
    if not os.path.exists(new_db):
        print(f'❌ Новая база не найдена: {new_db}')
        return False
    
    try:
        # Подключаемся к обеим базам
        # 1. Удаляем старые данные из новой базы
        new_conn = sqlite3.connect(new_db)
        new_cursor = new_conn.cursor()
        new_cursor.execute('DELETE FROM messages')
        new_cursor.execute('DELETE FROM chats')
        new_cursor.execute('DELETE FROM users')
        print('✅ Очищены данные в новой базе')
        
        # 2. Копируем данные из старой базы
        old_conn = sqlite3.connect(old_db)
        old_cursor = old_conn.cursor()
        
        # Копируем пользователей
        old_cursor.execute('SELECT * FROM users')
        users = old_cursor.fetchall()
        
        if users:
            for user in users:
                # Создаем SQL с правильным количеством параметров
                placeholders = ','.join(['?' for _ in range(len(user))])
                new_cursor.execute(f'INSERT INTO users VALUES ({placeholders})', user)
            print(f'✅ Скопировано пользователей: {len(users)}')
        
        # Копируем чаты
        old_cursor.execute('SELECT * FROM chats')
        chats = old_cursor.fetchall()
        
        if chats:
            for chat in chats:
                placeholders = ','.join(['?' for _ in range(len(chat))])
                new_cursor.execute(f'INSERT INTO chats VALUES ({placeholders})', chat)
            print(f'✅ Скопировано чатов: {len(chats)}')
        
        # Копируем сообщения (если есть)
        try:
            old_cursor.execute('SELECT * FROM messages')
            messages = old_cursor.fetchall()
            
            if messages:
                for msg in messages:
                    placeholders = ','.join(['?' for _ in range(len(msg))])
                    new_cursor.execute(f'INSERT INTO messages VALUES ({placeholders})', msg)
                print(f'✅ Скопировано сообщений: {len(messages)}')
        except:
            print('⚠️  Таблица messages не найдена в старой базе')
        
        # Фиксируем изменения
        new_conn.commit()
        
        # Проверяем результат
        print('\n=== РЕЗУЛЬТАТ ПЕРЕНОСА ===')
        
        # Считаем записи в новой базе
        new_cursor.execute('SELECT COUNT(*) FROM users')
        new_user_count = new_cursor.fetchone()[0]
        print(f'Пользователей в новой базе: {new_user_count}')
        
        new_cursor.execute('SELECT COUNT(*) FROM chats')
        new_chat_count = new_cursor.fetchone()[0]
        print(f'Чатов в новой базе: {new_chat_count}')
        
        try:
            new_cursor.execute('SELECT COUNT(*) FROM messages')
            new_msg_count = new_cursor.fetchone()[0]
            print(f'Сообщений в новой базе: {new_msg_count}')
        except:
            print(f'Сообщений в новой базе: 0 (таблица messages не создана)')
        
        # Закрываем соединения
        old_conn.close()
        new_conn.close()
        
        print('\n✅ ПЕРЕНОС ДАННЫХ УСПЕШНО ЗАВЕРШЕН!')
        print('Старые чаты из Vaito теперь в базе данных Docker-контейнера.')
        print('\nПерезапустите приложение:')
        print('  docker-compose down')
        print('  docker-compose up --build -d')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка при переносе данных: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('=== ПЕРЕНОС ДАННЫХ ИЗ СТАРОЙ БАЗЫ Vaito ===')
    print('Переносит старые чаты в базу Docker-контейнера')
    print()
    transfer_data()