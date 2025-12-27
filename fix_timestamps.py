import sqlite3
import re

conn = sqlite3.connect('osagaming_crm.db')
cursor = conn.cursor()

print('Fixing timestamps to ISO format...')

# Get all chats
cursor.execute('SELECT id, created_at, updated_at, last_activity_at, last_message_at, last_assigned_at, last_released_at, closed_at FROM chats')
chats = cursor.fetchall()

updated = 0
for chat in chats:
    chat_id = chat[0]
    fields = {
        'created_at': chat[1],
        'updated_at': chat[2],
        'last_activity_at': chat[3],
        'last_message_at': chat[4],
        'last_assigned_at': chat[5],
        'last_released_at': chat[6],
        'closed_at': chat[7]
    }
    
    updates = []
    values = []
    
    for field_name, value in fields.items():
        if value and not str(value).startswith('None'):
            # Convert '2025-12-14 20:40:55' to '2025-12-14T20:40:55'
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', value):
                iso_value = value.replace(' ', 'T')
                updates.append(f'{field_name} = ?')
                values.append(iso_value)
                updated += 1
    
    if updates:
        values.append(chat_id)
        query = f'UPDATE chats SET {', '.join(updates)} WHERE id = ?'
        cursor.execute(query, values)

conn.commit()
print(f'Updated {updated} timestamp fields')

# Check result
cursor.execute('SELECT id, created_at, updated_at, last_activity_at FROM chats LIMIT 3')
rows = cursor.fetchall()
print('\nAfter update:')
for row in rows:
    print(f'ID: {row[0]}, created_at: {repr(row[1])}, updated_at: {repr(row[2])}, last_activity_at: {repr(row[3])}')

conn.close()
print('Timestamps fixed!')
