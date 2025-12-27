import sqlite3
from passlib.context import CryptContext

# Hash the password 'admin123'
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
new_password = 'admin123'
new_hashed_password = pwd_context.hash(new_password)

print(f'New password: {new_password}')
print(f'New hash: {new_hashed_password}')

# Update the admin user's password in the database
conn = sqlite3.connect('/app/osagaming_crm.db')
cursor = conn.cursor()

print('Updating admin password...')
cursor.execute("UPDATE users SET hashed_password = ? WHERE email = 'admin@osagaming.com'", (new_hashed_password,))
conn.commit()

# Verify
cursor.execute("SELECT email, hashed_password FROM users WHERE email='admin@osagaming.com'")
user = cursor.fetchone()
if user:
    print(f'Admin user found: {user[0]}')
    print(f'Password hash updated: {user[1][:20]}...')
    
    # Test verification
    if pwd_context.verify(new_password, user[1]):
        print('Password verification: SUCCESS')
    else:
        print('Password verification: FAILED')
else:
    print('Admin user not found')

conn.close()
print('[SUCCESS] Admin password reset to: admin123')