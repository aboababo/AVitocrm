import sqlite3

def main():
    conn = sqlite3.connect('backend/osagaming_crm.db')
    cursor = conn.cursor()
    
    # Проверяем значения статусов
    print("Checking status values in chats table:")
    cursor.execute("SELECT id, status, priority FROM chats")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Status: '{row[1]}', Priority: '{row[2]}'")
        # Проверяем регистр
        if row[1] and row[1].islower():
            print(f"  WARNING: Status '{row[1]}' is lowercase!")
        if row[2] and row[2].islower():
            print(f"  WARNING: Priority '{row[2]}' is lowercase!")
    
    print("\nChecking status values in users table:")
    cursor.execute("SELECT id, status FROM users")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Status: '{row[1]}'")
        if row[1] and row[1].islower():
            print(f"  WARNING: Status '{row[1]}' is lowercase!")
    
    conn.close()

if __name__ == '__main__':
    main()