#!/usr/bin/env python3
"""
Скрипт для обновления пароля пользователя в базе данных.
"""

import bcrypt
import sqlite3

def update_user_password():
    """Обновляет пароль пользователя admin@osagaming.com на admin123"""
    
    db_path = 'backend/osagaming_crm.db'
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем текущих пользователей
        cursor.execute('SELECT email FROM users')
        users = cursor.fetchall()
        print(f'Текущие пользователи: {users}')
        
        # Хэшируем новый пароль
        new_password = 'admin123'
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Обновляем пароль
        cursor.execute(
            'UPDATE users SET hashed_password = ? WHERE email = ?',
            (hashed_password.decode('utf-8'), 'admin@osagaming.com')
        )
        
        if cursor.rowcount > 0:
            print(f'Пароль для admin@osagaming.com успешно обновлен')
            print(f'Новый пароль: {new_password}')
            
            # Проверяем обновление
            cursor.execute(
                'SELECT email, hashed_password FROM users WHERE email = ?',
                ('admin@osagaming.com',)
            )
            updated_user = cursor.fetchone()
            print(f'Обновленные данные: email={updated_user[0]}, hash={updated_user[1]}')
            
            # Проверяем что новый пароль работает
            if bcrypt.checkpw(new_password.encode('utf-8'), updated_user[1].encode('utf-8')):
                print('Проверка нового пароля успешна')
            else:
                print('Проверка нового пароля не удалась')
        else:
            print('Пользователь не найден')
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f'Ошибка при обновлении пароля: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('=== Обновление пароля пользователя ===')
    print('Пользователь: admin@osagaming.com')
    print('Новый пароль: admin123')
    print()
    
    if update_user_password():
        print('\nОбновление пароля завершено успешно!')
        print('Теперь можно использовать логин:')
        print('  Email: admin@osagaming.com')
        print('  Пароль: admin123')
        print('\nПерезапустите docker-compose для применения изменений.')
    else:
        print('\nНе удалось обновить пароль.')