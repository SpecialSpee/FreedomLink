# android_client/encryption.py — минимальная версия для сборки
# Позже заменим на полноценное шифрование

class CryptoManager:
    """Заглушка: возвращает данные как есть. Шифрование — на сервере."""
    
    def __init__(self, password: str):
        self.password = password  # можно использовать для хеширования на сервере
    
    def encrypt(self, plaintext: str) -> str:
        # Временно: без шифрования, просто возвращаем текст
        # Сервер зашифрует при получении
        return plaintext
    
    def decrypt(self, ciphertext: str) -> str:
        # Временно: без расшифровки
        # Сервер пришлёт уже расшифрованное, если нужно
        return ciphertext
    
    def encrypt_bytes(self,  bytes) -> bytes:
        return data
    
    def decrypt_bytes(self, token: bytes) -> bytes:
        return token