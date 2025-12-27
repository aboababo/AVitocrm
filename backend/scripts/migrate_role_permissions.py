#!/usr/bin/env python3
"""Миграция связей role_permissions -> role_permissions_assoc

Запускается из корня проекта или внутри контейнера.
Сценарии:
- если legacy таблица содержит role_id и permission_id — копирует напрямую;
- если legacy таблица хранит имена — сопоставляет по `roles.name` и `permissions.name`.
"""
import os
import sqlite3
import sys

base = os.path.dirname(os.path.dirname(__file__))  # backend/
db_path = os.path.join(base, "osagaming_crm.db")

if not os.path.exists(db_path):
    print("DB file not found:", db_path)
    sys.exit(2)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Создаём ассоциативную таблицу, если её нет
cur.execute("""
CREATE TABLE IF NOT EXISTS role_permissions_assoc (
  role_id INTEGER NOT NULL,
  permission_id INTEGER NOT NULL,
  PRIMARY KEY (role_id, permission_id)
)
""")
conn.commit()

# Проверяем наличие legacy таблицы
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role_permissions'")
if not cur.fetchone():
    print("Legacy table 'role_permissions' not found — миграция не требуется.")
    conn.close()
    sys.exit(0)

# Получаем колонки legacy таблицы
cur.execute("PRAGMA table_info(role_permissions)")
cols = [r[1] for r in cur.fetchall()]
print("role_permissions columns:", cols)

if 'role_id' in cols and 'permission_id' in cols:
    cur.execute("INSERT OR IGNORE INTO role_permissions_assoc (role_id, permission_id) SELECT DISTINCT role_id, permission_id FROM role_permissions")
    conn.commit()
    print("Скопировано mappings role_id/permission_id из role_permissions")
    conn.close()
    sys.exit(0)

# Пытаемся угадать колонки с именами
role_col = None
perm_col = None
for c in cols:
    lc = c.lower()
    if 'role' in lc and ('name' in lc or 'title' in lc or 'role' == lc):
        role_col = c
    if 'perm' in lc or 'permission' in lc:
        perm_col = c

if not role_col or not perm_col:
    print('Не удалось определить колонки role/permission в legacy таблице:', cols)
    conn.close()
    sys.exit(3)

cur.execute(f"SELECT DISTINCT {role_col}, {perm_col} FROM role_permissions")
rows = cur.fetchall()
inserted = 0
for role_name, perm_name in rows:
    if role_name is None or perm_name is None:
        continue
    cur.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
    r = cur.fetchone()
    if not r:
        print("Role not found (skipping):", role_name)
        continue
    role_id = r[0]
    cur.execute("SELECT id FROM permissions WHERE name = ?", (perm_name,))
    p = cur.fetchone()
    if not p:
        print("Permission not found (skipping):", perm_name)
        continue
    perm_id = p[0]
    try:
        cur.execute("INSERT OR IGNORE INTO role_permissions_assoc (role_id, permission_id) VALUES (?, ?)", (role_id, perm_id))
        inserted += 1
    except Exception as e:
        print("Insert error:", e)

conn.commit()
print(f"Inserted {inserted} mappings from name-based legacy table")
conn.close()
