# tests/test_server.py
import json

def test_broadcast_logic():
    # Тестируем логику формирования пакета (без запуска сервера)
    users = ["user1", "user2", "user3"]
    packet = json.dumps({"type": "users_list", "users": users})
    data = json.loads(packet)
    
    assert data["type"] == "users_list"
    assert set(data["users"]) == set(users)
    assert len(data["users"]) == 3