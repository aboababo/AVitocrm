import sqlite3

p = 'osagaming_crm.db'
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("""INSERT INTO users (email, hashed_password, first_name, last_name, is_active, is_superuser, is_verified, status, email_notifications, push_notifications) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("admin@osagaming.com",
             "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8j1G1v7e1O",
             "Admin", "User", 1, 1, 1, "active", 1, 1))
conn.commit()
print('inserted', cur.lastrowid)
conn.close()
