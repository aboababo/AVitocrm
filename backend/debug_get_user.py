import sqlite3
c=sqlite3.connect('/app/osagaming_crm.db')
cur=c.cursor()
cur.execute('select id,email,hashed_password from users where email=?', ('admin@osagaming.com',))
row=cur.fetchone()
print(row)
c.close()
