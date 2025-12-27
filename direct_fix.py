#!/usr/bin/env python3
"""
Прямое исправление данных в базе данных через SQLite
"""

import sqlite3

def direct_fix():
    """Прямое исправление данных"""
    
    db_path = 'backend/osagaming_crm.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("1. Удаляем текущие чаты и сообщения...")
    cursor.execute('DELETE FROM messages')
    cursor.execute('DELETE FROM chats')
    
    print("2. Создаем новые чаты с правильными именами...")
    
    # Имена в UTF-8 кодировке
    test_data = """
    INSERT INTO chats (user_id, client_name, client_phone, title, description, priority, status, message_count, unread_count, created_at, updated_at) VALUES
    (1, 'Иван Иванов', '+79161112233', 'Вопрос по доставке', 'Клиент интересуется сроком доставки заказа', 'NORMAL', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Мария Петрова', '+79162223344', 'Проблема с оплатой', 'Не может оплатить онлайн заказ', 'HIGH', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Алексей Сидоров', '+79163334455', 'Консультация', 'Нужна помощь в выборе товара', 'LOW', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Ольга Козлова', '+79164445566', 'Жалоба', 'Получен товар с браком', 'URGENT', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Сергей Волков', '+79165556677', 'Гарантия', 'Вопрос по гарантийному обслуживанию', 'NORMAL', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Анна Морозова', '+79166667788', 'Сотрудничество', 'Запрос на партнерство', 'HIGH', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Дмитрий Смирнов', '+79167778899', 'Консультация', 'Нужна помощь по продукту', 'NORMAL', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Екатерина Орлова', '+79168889900', 'Техническая проблема', 'Не работает сайт', 'URGENT', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Михаил Лебедев', '+79169990011', 'Акция', 'Вопрос по участию в акции', 'LOW', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Татьяна Соколова', '+79160001122', 'Отзыв', 'Оставляет отзыв о сервисе', 'NORMAL', 'ACTIVE', 0, 0, datetime('now'), datetime('now')),
    (1, 'Андрей Павлов', '+79161112233', 'Возврат', 'Хочет вернуть товар по гарантии', 'HIGH', 'ACTIVE', 0, 0, datetime('now'), datetime('now'));
    """
    
    try:
        cursor.execute(test_data)
        print("✅ Тестовые данные созданы")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        # Попробуем создать по одному
        chats = [
            (1, 'Иван Иванов', '+79161112233', 'Вопрос по доставке', 'Клиент интересуется сроком доставки заказа', 'NORMAL', 'ACTIVE', 0, 0),
            (1, 'Мария Петрова', '+79162223344', 'Проблема с оплатой', 'Не может оплатить онлайн заказ', 'HIGH', 'ACTIVE', 0, 0),
            (1, 'Алексей Сидоров', '+79163334455', 'Консультация', 'Нужна помощь в выборе товара', 'LOW', 'ACTIVE', 0, 0),
            (1, 'Ольга Козлова', '+79164445566', 'Жалоба', 'Получен товар с браком', 'URGENT', 'ACTIVE', 0, 0),
            (1, 'Сергей Волков', '+79165556677', 'Гарантия', 'Вопрос по гарантийному обслуживанию', 'NORMAL', 'ACTIVE', 0, 0),
            (1, 'Анна Морозова', '+79166667788', 'Сотрудничество', 'Запрос на партнерство', 'HIGH', 'ACTIVE', 0, 0),
            (1, 'Дмитрий Смирнов', '+79167778899', 'Консультация', 'Нужна помощь по продукту', 'NORMAL', 'ACTIVE', 0, 0),
            (1, 'Екатерина Орлова', '+79168889900', 'Техническая проблема', 'Не работает сайт', 'URGENT', 'ACTIVE', 0, 0),
            (1, 'Михаил Лебедев', '+79169990011', 'Акция', 'Вопрос по участию в акции', 'LOW', 'ACTIVE', 0, 0),
            (1, 'Татьяна Соколова', '+79160001122', 'Отзыв', 'Оставляет отзыв о сервисе', 'NORMAL', 'ACTIVE', 0, 0),
            (1, 'Андрей Павлов', '+79161112233', 'Возврат', 'Хочет вернуть товар по гарантии', 'HIGH', 'ACTIVE', 0, 0)
        ]
        
        for chat in chats:
            try:
                cursor.execute('''
                    INSERT INTO chats 
                    (user_id, client_name, client_phone, title, description, priority, status, message_count, unread_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ''', chat)
                print(f"   Создан чат: {chat[1]}")
            except Exception as e2:
                print(f"   Ошибка создания чата {chat[1]}: {e2}")
    
    conn.commit()
    
    print("\n3. Проверяем созданные данные...")
    cursor.execute("SELECT id, client_name, priority, status FROM chats")
    rows = cursor.fetchall()
    
    print(f"Всего чатов: {len(rows)}")
    print("Первые 5 записей:")
    for row in rows[:5]:
        print(f"  ID:{row[0]}, Имя: '{row[1]}', Приоритет: '{row[2]}', Статус: '{row[3]}'")
    
    # Проверяем кодировку
    print("\n4. Проверка кодировки...")
    for row in rows[:3]:
        name = row[1]
        print(f"  Имя: {name}")
        print(f"    Длина: {len(name)}")
        print(f"    Байты: {repr(name.encode('utf-8'))}")
        print(f"    Символы по одному:")
        for char in name:
            print(f"      '{char}' (код: {ord(char)})")
    
    conn.close()
    
    print("\n✅ Готово! Данные исправлены.")
    print("Перезапустите приложение:")
    print("  docker-compose down")
    print("  docker-compose up --build -d")

if __name__ == '__main__':
    direct_fix()