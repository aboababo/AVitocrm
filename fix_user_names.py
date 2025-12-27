import sqlite3

conn = sqlite3.connect('osagaming_crm.db')
cursor = conn.cursor()

# Fill first_name and last_name with default values
cursor.execute('UPDATE users SET first_name = \"Admin\" WHERE first_name = \"\" AND email LIKE \"%admin%\"')
cursor.execute('UPDATE users SET first_name = \"Manager\" WHERE first_name = \"\" AND email LIKE \"%gmail%\"')
cursor.execute('UPDATE users SET first_name = \"User\" WHERE first_name = \"\"')

# Set default last_name
cursor.execute('UPDATE users SET last_name = \"User\" WHERE last_name = \"\"')

conn.commit()

# Check result
cursor.execute('SELECT id, email, first_name, last_name FROM users')
for row in cursor.fetchall():
    print(f'ID:{row[0]}, Email: {row[1]}, First: \"{row[2]}\", Last: \"{row[3]}\"')

conn.close()
print('Updated user names')
