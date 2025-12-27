#!/usr/bin/env python3
"""Выводит содержимое legacy role_permissions для диагностики миграции."""
import os, sqlite3, sys

base = os.path.dirname(os.path.dirname(__file__))
db_path = os.path.join(base, "osagaming_crm.db")
if not os.path.exists(db_path):
    print('DB not found:', db_path); sys.exit(2)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role_permissions'")
if not cur.fetchone():
    print("No role_permissions table")
    conn.close(); sys.exit(0)

print('role_permissions rows (sample up to 50):')
cur.execute('SELECT * FROM role_permissions LIMIT 50')
rows = cur.fetchall()
for r in rows:
    print(r)

cur.execute('PRAGMA table_info(role_permissions)')
print('\nColumns:')
for c in cur.fetchall():
    print(c)

cur.execute('SELECT COUNT(1) FROM role_permissions')
print('\nTotal rows:', cur.fetchone()[0])

cur.execute('SELECT DISTINCT role FROM role_permissions')
print('\nDistinct roles:')
for r in cur.fetchall():
    print(r[0])

cur.execute('SELECT DISTINCT permission_key FROM role_permissions')
print('\nDistinct permission_key:')
for r in cur.fetchall():
    print(r[0])

conn.close()
