import sqlite3

conn = sqlite3.connect('/app/osagaming_crm.db')
cursor = conn.cursor()

# Check admin user password hash
cursor.execute("SELECT email, hashed_password FROM users WHERE email='admin@osagaming.com'")
user = cursor.fetchone()

if user:
    print(f'Email: {user[0]}')
    print(f'Hashed password: {user[1]}')
    print(f'Hash length: {len(user[1]) if user[1] else 0}')
    
    # Check if password is plaintext (not bcrypt hash)
    if user[1] and not user[1].startswith('$2b$'):
        print('WARNING: Password is NOT a bcrypt hash!')
        print('Password is plaintext, needs to be hashed')
else:
    print('Admin user not found')

conn.close()