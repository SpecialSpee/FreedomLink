# fix_db.py — запускать при повреждении БД
import os
import sqlite3

DB_PATH = "chat_history.db"

def fix_database():
    if os.path.exists(DB_PATH):
        print(f"🗑️ Removing corrupted {DB_PATH}...")
        try:
            os.remove(DB_PATH)
            print("✅ Removed")
        except PermissionError:
            print("⚠️ File locked. Please close all Python processes and try again.")
            return
    
    print("🔨 Creating fresh database...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            delivered INTEGER DEFAULT 1,
            encrypted INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            registered_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS global_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            is_file INTEGER DEFAULT 0,
            file_id TEXT,
            filename TEXT,
            file_size INTEGER,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database ready!")

if __name__ == "__main__":
    fix_database()