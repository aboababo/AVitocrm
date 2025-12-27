import sqlite3
import bcrypt

# Hash password 'admin123'
new_password = b'admin123'
new_hashed_password = bcrypt.hashpw(new_password, bcrypt.gensalt())

print(f'New password: {new_password.decode()}')
print(f'New hash: {new_hashed_password.decode()}')

# Update admin user's password in database
conn = sqlite3.connect('/app/osagaming_crm.db')
cursor = conn.cursor()

print('Updating admin password...')
cursor.execute("UPDATE users SET hashed_password = ? WHERE email = 'admin@osagaming.com'", (new_hashed_password.decode(),))
conn.commit()

# Verify
cursor.execute("SELECT email, hashed_password FROM users WHERE email='admin@osagaming.com'")
user = cursor.fetchone()
if user:
    print(f'Admin user found: {user[0]}')
    print(f'Password hash updated: {user[1][:20]}...')
    
    # Test verification
    if bcrypt.checkpw(new_password, user[1].encode()):
        print('Password verification: SUCCESS')
    else:
        print('Password verification: FAILED')
else:
    print('Admin user not found')

conn.close()
print('[SUCCESS] Admin password reset to: admin123')