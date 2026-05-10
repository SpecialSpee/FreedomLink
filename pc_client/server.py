import asyncio
import websockets
import json
import logging
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# 🔐 НАСТРОЙКА ЛОГГЕРА — ДОЛЖНА БЫТЬ ПЕРВОЙ!
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "chat_history.db")
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8765))

# 🔐 Persistent user registry
REGISTRY_FILE = "users.json"
USER_REGISTRY: dict[str, str] = {}
GLOBAL_CHAT_HISTORY: list = []  # Кэш последних сообщений (опционально)

def _load_registry() -> None:
    """Загружает реестр из файла при старте"""
    global USER_REGISTRY
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                USER_REGISTRY = json.load(f)
            logger.info(f"📦 Loaded {len(USER_REGISTRY)} users from {REGISTRY_FILE}")
        except Exception as e:
            logger.error(f"⚠️ Failed to load registry: {e}. Starting fresh.")
            USER_REGISTRY = {}
    else:
        logger.info(f"📝 No registry file found, starting fresh: {REGISTRY_FILE}")

def _save_registry() -> None:
    """Сохраняет реестр на диск после изменений"""
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_REGISTRY, f, indent=2)
    except Exception as e:
        logger.error(f"💥 Failed to save registry: {e}")

# Загружаем реестр ПОСЛЕ инициализации logger
_load_registry()

connected_clients = {}

async def broadcast_users_list():
    if not connected_clients:
        return
    users = list(connected_clients.keys())
    packet = json.dumps({"type": "users_list", "users": users})
    logger.info(f"📢 Broadcasting list to {len(users)}: {users}")
    tasks = []
    for uid, ws in list(connected_clients.items()):
        tasks.append(_safe_send(ws, packet, uid))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def _safe_send(ws, msg, uid):
    try:
        await ws.send(msg)
        logger.debug(f"✅ Sent to {uid}")
    except websockets.exceptions.ConnectionClosed:
        logger.warning(f"🗑️ {uid} disconnected during broadcast.")
        connected_clients.pop(uid, None)
    except websockets.exceptions.InvalidState:
        logger.warning(f"⚠️ {uid} connection invalid (removing...)")
        connected_clients.pop(uid, None)
    except Exception as e:
        logger.error(f"❌ Send failed to {uid}: {e}")
        connected_clients.pop(uid, None)

async def handle_client(websocket):
    user_id = None
    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "auth":
                user_id = data.get("user_id")
                pwd_hash = data.get("password")
                
                # ✅ Валидация кредов
                if not user_id or not pwd_hash:
                    await websocket.send(json.dumps({"type": "error", "content": "AUTH_FAILED: Missing credentials"}))
                    await websocket.close()
                    return

                # ✅ Проверка пароля или регистрация нового пользователя
                if user_id in USER_REGISTRY:
                    if USER_REGISTRY[user_id] != pwd_hash:
                        await websocket.send(json.dumps({"type": "error", "content": "AUTH_FAILED: Invalid password"}))
                        logger.warning(f"🚫 {user_id} failed login attempt")
                        await websocket.close()
                        return
                else:
                    # Новый пользователь — сохраняем хеш
                    USER_REGISTRY[user_id] = pwd_hash
                    _save_registry()
                    logger.info(f"📝 New user registered: {user_id}")
                    
                # ✅ Обработка реконнекта: закрываем старое соединение
                if user_id in connected_clients:
                    old_ws = connected_clients[user_id]
                    try:
                        await old_ws.close()
                        logger.info(f"🔄 {user_id} reconnected (old connection closed)")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to close old connection for {user_id}: {e}")
                
                await asyncio.sleep(0.05)
                connected_clients[user_id] = websocket
                logger.info(f"✅ {user_id} authorized.")
                
                await websocket.send(json.dumps({"type": "welcome", "content": "Connected"}))
                await websocket.send(json.dumps({"type": "users_list", "users": list(connected_clients.keys())}))
                
                if len(connected_clients) > 1:
                    await broadcast_users_list()

            elif msg_type == "chat":
                receiver = data.get("receiver")
                target_ws = connected_clients.get(receiver)
                if target_ws:
                    try:
                        await target_ws.send(json.dumps(data))
                        logger.info(f"💬 Message from {user_id} to {receiver}")
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(f"⚠️ {receiver} seems offline, removing...")
                        del connected_clients[receiver]
                        await websocket.send(json.dumps({"type": "error", "content": f"User {receiver} is offline"}))
                else:
                    await websocket.send(json.dumps({"type": "error", "content": f"User {receiver} is offline"}))

            # ✅ ПЕРЕДАЧА ФАЙЛА (личная)
            elif msg_type == "file_transfer":
                receiver = data.get("receiver")
                target_ws = connected_clients.get(receiver)
                
                logger.info(f"📁 File transfer: from={user_id} to={receiver} size={data.get('size')}")
                
                if target_ws:
                    try:
                        # ✅ Форвардим файл получателю
                        await target_ws.send(json.dumps(data))
                        logger.info(f"✅ File forwarded to {receiver}")
                        
                        # ✅ Опционально: подтверждаем отправителю
                        await websocket.send(json.dumps({
                            "type": "file_sent_ok",
                            "file_id": data.get("file_id")
                        }))
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(f"⚠️ {receiver} disconnected during file transfer")
                        del connected_clients[receiver]
                        await websocket.send(json.dumps({"type": "error", "content": f"{receiver} offline"}))
                else:
                    logger.warning(f"⚠️ Receiver {receiver} not found")
                    await websocket.send(json.dumps({"type": "error", "content": f"User {receiver} is offline"}))

            # ✅ ГЛОБАЛЬНЫЙ ЧАТ
            elif msg_type == "global_chat":
                sender = user_id
                text = data.get("text", "")
                is_file = data.get("is_file", False)
                file_id = data.get("file_id")
                filename = data.get("filename")
                file_size = data.get("size")
                file_data = data.get("data")
                
                logger.info(f"📥 Global from {sender}: text={text[:30] if text else '[FILE]'}..., is_file={is_file}")
                logger.info(f"👥 Connected: {list(connected_clients.keys())}")
                
                # ✅ Сохраняем в БД
                from database import save_global_message
                try:
                    save_global_message(
                        sender=sender, 
                        text=text if not is_file else f"[FILE] {filename}",
                        is_file=is_file,
                        file_id=file_id, 
                        filename=filename, 
                        file_size=file_size
                    )
                    logger.info(f"💾 Saved to DB")
                except Exception as e:
                    logger.error(f"❌ DB save failed: {e}")
                
                # ✅ Формируем пакет для рассылки
                timestamp = datetime.now().isoformat()
                
                if is_file:
                    # 📎 Для файлов <1 МБ: шлём данные сразу
                    if file_size < 1024 * 1024:
                        packet = json.dumps({
                            "type": "global_chat",
                            "sender": sender,
                            "text": "",
                            "is_file": True,
                            "file_id": file_id,
                            "filename": filename,
                            "size": file_size,
                            "data": file_data,
                            "timestamp": timestamp
                        })
                        logger.info(f"📎 Broadcasting FILE + DATA: {filename} ({file_size} bytes)")
                    else:
                        # Для больших: только метаданные
                        packet = json.dumps({
                            "type": "global_chat",
                            "sender": sender,
                            "text": "",
                            "is_file": True,
                            "file_id": file_id,
                            "filename": filename,
                            "size": file_size,
                            "timestamp": timestamp
                        })
                        logger.info(f"📎 Broadcasting FILE METADATA ONLY: {filename} ({file_size} bytes)")
                else:
                    # 💬 Для текста: шлём как есть
                    packet = json.dumps({
                        "type": "global_chat",
                        "sender": sender,
                        "text": text,
                        "is_file": False,
                        "timestamp": timestamp
                    })
                    logger.info(f"💬 Broadcasting TEXT: {text[:50]}...")
                
                # ✅ Рассылаем всем (packet теперь определён всегда)
                tasks = []
                for uid, ws in list(connected_clients.items()):
                    tasks.append(_safe_send(ws, packet, uid))
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info(f"✅ Broadcast complete to {len(connected_clients)} clients")
                
            # ✅ ЗАПРОС ФАЙЛА ИЗ ГЛОБАЛЬНОГО ЧАТА
            elif msg_type == "request_global_file":
                file_id = data.get("file_id")
                from database import get_global_file_data  # ← Нужно добавить в database.py
                file_record = get_global_file_data(file_id)
                
                if file_record:
                    # Отправляем файл ТОЛЬКО запрашивающему
                    await websocket.send(json.dumps({
                        "type": "global_file_data",
                        "file_id": file_id,
                        "filename": file_record["filename"],
                        "data": file_record["file_data"]  # Base64 encrypted
                    }))
                    logger.info(f"📤 Sent file {file_id} to {user_id}")
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "content": "File not found"
                    }))

            # ✅ Смена пароля
            elif msg_type == "change_password":
                old_hash = data.get("old_password")
                new_hash = data.get("new_password")
                if user_id and USER_REGISTRY.get(user_id) == old_hash and new_hash:
                    USER_REGISTRY[user_id] = new_hash
                    _save_registry()
                    await websocket.send(json.dumps({"type": "success", "content": "Password updated"}))
                    logger.info(f"🔑 {user_id} changed password")
                else:
                    await websocket.send(json.dumps({"type": "error", "content": "AUTH_FAILED"}))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"🔌 {user_id or 'Unknown'} disconnected.")
    except Exception as e:
        logger.error(f"💥 Handler error: {e}")
    finally:
        # ✅ Race-condition fix: удаляем только если это наше соединение
        if user_id and connected_clients.get(user_id) is websocket:
            del connected_clients[user_id]
            logger.info(f"❌ {user_id} removed.")
            if connected_clients:
                await broadcast_users_list()

async def main():
    async with websockets.serve(handle_client, SERVER_HOST, SERVER_PORT):
        logger.info(f"🚀 Server running on ws://{SERVER_HOST}:{SERVER_PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped.")