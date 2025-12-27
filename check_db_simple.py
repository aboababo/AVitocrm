import sqlite3
import os

db_path = 'backend/osagaming_crm.db'
if not os.path.exists(db_path):
    print('Database not found:', db_path)
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Tables in database:')
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f'  {table[0]}: {count} records')
    
    # Check data in chats table
    cursor.execute("SELECT id, client_name, title, priority, status FROM chats")
    chats = cursor.fetchall()
    print(f'\nChats in database: {len(chats)}')
    for chat in chats:
        print(f'  ID:{chat[0]}, Name: {chat[1]}, Title: {chat[2]}, Priority: {chat[3]}, Status: {chat[4]}')
    
    conn.close()