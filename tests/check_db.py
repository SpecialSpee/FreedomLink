import sqlite3

conn = sqlite3.connect("chat_history.db")
cursor = conn.cursor()

print(" ТАБЛИЦЫ В БД:")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables: print(f"  - {t[0]}")

print("\n👥 ЮЗЕРЫ В ТАБЛИЦЕ 'users':")
try:
    users = cursor.execute("SELECT user_id, registered_at FROM users").fetchall()
    if users:
        for u in users: print(f"  - {u[0]} (зарег: {u[1]})")
    else:
        print("  ⚠️ Таблица есть, но ПУСТАЯ!")
except sqlite3.OperationalError as e:
    print(f"  ❌ Таблицы 'users' нет: {e}")

conn.close()
input("\nНажми Enter чтобы закрыть...")
