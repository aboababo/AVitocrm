import sqlite3
import bcrypt
pw = b'password'
h = bcrypt.hashpw(pw, bcrypt.gensalt())
conn = sqlite3.connect('osagaming_crm.db')
cur = conn.cursor()
cur.execute('update users set hashed_password=? where email=?', (h.decode(), 'admin@osagaming.com'))
conn.commit()
print('updated', cur.rowcount)
conn.close()
