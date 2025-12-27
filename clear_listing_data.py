#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('backend/osagaming_crm.db')
cursor = conn.cursor()

# Check listing_data values
cursor.execute("SELECT COUNT(*) FROM chats WHERE listing_data LIKE '{%'")
count = cursor.fetchone()[0]
print(f'Found {count} chats with JSON in listing_data')

if count > 0:
    # Clear listing_data
    cursor.execute("UPDATE chats SET listing_data = NULL WHERE listing_data LIKE '{%'")
    conn.commit()
    print('Cleared listing_data from all chats')
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM chats WHERE listing_data LIKE '{%'")
    new_count = cursor.fetchone()[0]
    print(f'Remaining: {new_count}')

conn.close()
print('Done!')