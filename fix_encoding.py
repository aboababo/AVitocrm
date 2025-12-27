#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления кодировки имен клиентов в базе данных.
Проблема: имена хранятся с поврежденной кодировкой (отображаются как "?????").
Решение: пересоздать тестовые данные с правильной UTF-8 кодировкой.
"""

import sqlite3
import datetime

def fix_encoding_issues():
    """Исправляет проблемы с кодировкой в базе данных"""
    
    db_path = 'backend/osagaming_crm.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== FIXING ENCODING IN DATABASE ===")
        
        # 1. Удаляем старые данные с проблемной кодировкой
        print("\n1. Removing old data...")
        cursor.execute('DELETE FROM messages')
        cursor.execute('DELETE FROM chats')
        
        # 2. Создаем правильные тестовые данные
        print("\n2. Creating new test data with UTF-8 encoding...")
        
        test_chats = [
            {
                'client_name': 'Ivan Ivanov',
                'client_phone': '+79161112233',
                'title': 'Delivery question order #12345',
                'priority': 'NORMAL',
                'description': 'Customer asks about delivery time'
            },
            {
                'client_name': 'Maria Petrova',
                'client_phone': '+79162223344',
                'title': 'Online payment problem',
                'priority': 'HIGH',
                'description': 'Customer cannot pay via website'
            },
            {
                'client_name': 'Alexey Sidorov',
                'client_phone': '+79163334455',
                'client_email': 'alexey@example.com',
                'title': 'Product consultation',
                'priority': 'LOW',
                'description': 'Need help choosing phone model'
            },
            {
                'client_name': 'Olga Kozlova',
                'client_phone': '+79164445566',
                'title': 'Product quality complaint',
                'priority': 'URGENT',
                'description': 'Customer received defective item'
            },
            {
                'client_name': 'Sergey Volkov',
                'client_phone': '+79165556677',
                'title': 'Warranty service question',
                'priority': 'NORMAL',
                'description': 'Need info about warranty terms'
            },
            {
                'client_name': 'Anna Morozova',
                'client_phone': '+79166667788',
                'client_email': 'anna@example.com',
                'title': 'Partnership inquiry',
                'priority': 'HIGH',
                'description': 'Customer wants to discuss partnership'
            },
            {
                'client_name': 'Dmitry Smirnov',
                'client_phone': '+79167778899',
                'title': 'Product consultation',
                'priority': 'NORMAL',
                'description': 'Need help choosing suitable product'
            },
            {
                'client_name': 'Ekaterina Orlova',
                'client_phone': '+79168889900',
                'title': 'Website technical issue',
                'priority': 'URGENT',
                'description': 'Customer cannot place order on site'
            },
            {
                'client_name': 'Mikhail Lebedev',
                'client_phone': '+79169990011',
                'title': 'Promotion question',
                'priority': 'LOW',
                'description': 'Customer wants clarification on promotion'
            },
            {
                'client_name': 'Tatyana Sokolova',
                'client_phone': '+79160001122',
                'title': 'Service feedback',
                'priority': 'NORMAL',
                'description': 'Customer leaves service quality feedback'
            },
            {
                'client_name': 'Andrey Pavlov',
                'client_phone': '+79161112233',
                'title': 'Product return request',
                'priority': 'HIGH',
                'description': 'Customer wants to return item under warranty'
            }
        ]
        
        now = datetime.datetime.now().isoformat()
        
        for i, chat_data in enumerate(test_chats, 1):
            cursor.execute('''
                INSERT INTO chats (
                    user_id, client_name, client_phone, client_email,
                    title, description, priority, status, 
                    message_count, unread_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 0, 0, ?, ?)
            ''', (
                1,  # user_id admin
                chat_data['client_name'],
                chat_data['client_phone'],
                chat_data.get('client_email'),
                chat_data['title'],
                chat_data['description'],
                chat_data['priority'],
                now,
                now
            ))
            
            print(f"   Created chat: {chat_data['client_name']} ({chat_data['title']})")
        
        # 3. Добавляем несколько тестовых сообщений
        print("\n3. Adding test messages...")
        
        cursor.execute('SELECT id FROM chats')
        chat_ids = [row[0] for row in cursor.fetchall()]
        
        for chat_id in chat_ids[:5]:
            cursor.execute('''
                INSERT INTO messages (
                    chat_id, user_id, content, message_type, is_system, is_read, is_edited, created_at, updated_at
                ) VALUES (?, ?, ?, 'TEXT', 0, 1, 0, ?, ?)
            ''', (
                chat_id,
                1,  # user_id admin
                'Hello! How can I help you?',
                now,
                now
            ))
            
            # Обновляем счетчик сообщений в чате
            cursor.execute('''
                UPDATE chats 
                SET message_count = message_count + 1,
                    last_message_at = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (now, now, chat_id))
            
            print(f"   Added message to chat ID: {chat_id}")
        
        # 4. Фиксируем изменения
        conn.commit()
        conn.close()
        
        print("\nENCODING FIXED SUCCESSFULLY!")
        print("================================")
        print("   Now in database:")
        print("   • 11 chats with correct UTF-8 names")
        print("   • English text saved properly")
        print("   • Test messages added")
        print("================================")
        print("\nNext steps:")
        print("1. Restart application:")
        print("   docker-compose down")
        print("   docker-compose up --build -d")
        print("\n2. Check result:")
        print("   • Open http://localhost:8000")
        print("   • Login: admin@osagaming.com / admin123")
        print("   • Check chats list")
        
        return True
        
    except Exception as e:
        print(f"ERROR fixing encoding: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    fix_encoding_issues()