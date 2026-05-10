import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

DB_PATH = "chat_history.db"

def get_global_file_data(file_id: str, path: str = DB_PATH) -> Optional[dict]:
    """Получает данные файла по file_id"""
    init_global_chat_db(path)
    with sqlite3.connect(path, check_same_thread=False) as conn:
        cursor = conn.execute("""
            SELECT filename, file_size, text  -- text хранит "[FILE] name" или данные
            FROM global_messages 
            WHERE file_id = ? AND is_file = 1
        """, (file_id,))
        row = cursor.fetchone()
        if row:
            return {"filename": row[0], "size": row[1], "file_data": row[2]}
        return None

def _is_valid_db(path: str) -> bool:
    """Проверяет, является ли файл валидной SQLite БД"""
    if not os.path.exists(path):
        return True  # Файла нет — создадим новый, это ок
    
    try:
        # Быстрая проверка: читаем magic header SQLite
        with open(path, "rb") as f:
            header = f.read(16)
            if not header.startswith(b"SQLite format 3"):
                return False
        
        # Дополнительная проверка: пробуем выполнить простой запрос
        with sqlite3.connect(path, check_same_thread=False) as conn:
            conn.execute("SELECT 1")
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return True
    except Exception:
        return False

def _nuke_db(path: str) -> None:
    """Безопасное удаление повреждённой БД"""
    try:
        if os.path.exists(path):
            # 🔥 Параноик-режим: затирание перед удалением
            size = os.path.getsize(path)
            with open(path, "r+b") as f:
                f.write(b"\x00" * size)
                f.flush()
                os.fsync(f.fileno())
            os.remove(path)
            logger.warning(f"🗑️ Corrupted DB removed: {path}")
    except Exception as e:
        logger.error(f"Failed to remove corrupted DB: {e}")
        # Пробуем просто удалить без затирания
        try:
            os.remove(path)
        except:
            pass

def _ensure_table_exists(path: str = DB_PATH) -> bool:
    """Проверяет, существует ли таблица messages"""
    try:
        with sqlite3.connect(path, check_same_thread=False) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            )
            return cursor.fetchone() is not None
    except:
        return False

def init_db(path: str = DB_PATH) -> None:
    """Инициализация БД с проверкой целостности"""
    # ✅ Проверяем, не повреждён ли файл
    if not _is_valid_db(path):
        logger.warning(f"⚠️ DB file invalid or corrupted: {path}. Rebuilding...")
        _nuke_db(path)
    
    try:
        with sqlite3.connect(path, check_same_thread=False) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_pair ON messages(sender, receiver)")
            conn.commit()
            logger.info(f"✅ DB initialized: {path}")
    except sqlite3.Error as e:
        logger.error(f"💥 DB init failed: {e}")
        # Если не удалось создать — удаляем и пробуем ещё раз
        _nuke_db(path)
        raise

def save_message(sender: str, receiver: str, text: str, path: str = DB_PATH) -> None:
    """Сохранение сообщения с авто-восстановлением при сбое"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            if not _is_valid_db(path):
                _nuke_db(path)
            
            with sqlite3.connect(path, check_same_thread=False) as conn:
                conn.execute(
                    "INSERT INTO messages (sender, receiver, text, timestamp) VALUES (?, ?, ?, ?)",
                    (sender, receiver, text, datetime.now().isoformat())
                )
                conn.commit()
            return  # Успех
        except sqlite3.DatabaseError as e:
            if "file is not a database" in str(e) or "malformed" in str(e).lower():
                logger.warning(f"🔄 DB corrupted (attempt {attempt+1}), rebuilding...")
                _nuke_db(path)
                continue
            logger.error(f"DB error: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error saving message: {e}")
            break

def get_chat_history(user_a: str, user_b: str, path: str = DB_PATH) -> List[Tuple[str, str, str]]:
    """Получение истории с авто-восстановлением"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            if not _is_valid_db(path):
                _nuke_db(path)
                init_db(path)  # Пересоздаём структуру
            
            with sqlite3.connect(path, check_same_thread=False) as conn:
                cursor = conn.execute("""
                    SELECT sender, text, timestamp FROM messages
                    WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
                    ORDER BY timestamp ASC
                """, (user_a, user_b, user_b, user_a))
                return cursor.fetchall()
                
        except sqlite3.DatabaseError as e:
            if "file is not a database" in str(e) or "malformed" in str(e).lower():
                logger.warning(f"🔄 DB corrupted during read (attempt {attempt+1}), rebuilding...")
                _nuke_db(path)
                init_db(path)
                continue
            logger.error(f"DB read error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading history: {e}")
            return []

# === НОВЫЕ ФУНКЦИИ ДЛЯ ГЛОБАЛЬНОГО ЧАТА ===

def init_global_chat_db(path: str = DB_PATH) -> None:
    """Создаёт таблицу глобального чата"""
    with sqlite3.connect(path, check_same_thread=False) as conn:
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_global_ts ON global_messages(timestamp DESC)")
        conn.commit()

def save_global_message(sender: str, text: str, path: str = DB_PATH, 
                       is_file: bool = False, file_id: str = None, 
                       filename: str = None, file_size: int = None) -> None:
    """Сохраняет сообщение в глобальный чат"""
    if not _ensure_table_exists(path):
        init_db(path)
    init_global_chat_db(path)
    
    with sqlite3.connect(path, check_same_thread=False) as conn:
        conn.execute("""
            INSERT INTO global_messages (sender, text, is_file, file_id, filename, file_size, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sender, text, int(is_file), file_id, filename, file_size, datetime.now().isoformat()))
        conn.commit()

def get_global_chat_history(limit: int = 100, path: str = DB_PATH) -> List[dict]:
    """Получает последние сообщения глобального чата"""
    init_global_chat_db(path)
    with sqlite3.connect(path, check_same_thread=False) as conn:
        cursor = conn.execute("""
            SELECT sender, text, is_file, file_id, filename, file_size, timestamp
            FROM global_messages ORDER BY timestamp ASC LIMIT ?
        """, (limit,))
        return [
            {
                "sender": row[0], "text": row[1], "is_file": bool(row[2]),
                "file_id": row[3], "filename": row[4], "file_size": row[5], "timestamp": row[6]
            }
            for row in cursor.fetchall()
        ]

    return []