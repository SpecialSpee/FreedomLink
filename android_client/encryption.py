# android_client/encryption.py
# ✅ Кроссплатформенный крипто-менеджер:
# - На ПК: cryptography.fernet (быстро, надёжно)
# - На Android: simple-crypt (чистый Python, работает без компиляции)

import platform
import base64
import hashlib

# Определяем платформу
IS_ANDROID = platform.system() == "Android" or "ANDROID_ARGUMENT" in __import__("os").environ

if IS_ANDROID:
    # 🤖 Android: используем simple-crypt (чистый Python)
    try:
        from simplecrypt import encrypt as sc_encrypt, decrypt as sc_decrypt
        HAS_CRYPTO = True
    except ImportError:
        HAS_CRYPTO = False
        # Fallback для отладки: без шифрования
        def sc_encrypt(key, data): return data.encode() if isinstance(data, str) else data
        def sc_decrypt(key, data): return data.decode() if isinstance(data, bytes) else data
else:
    # 🖥️ ПК: используем cryptography.fernet (оригинальная реализация)
    try:
        from cryptography.fernet import Fernet
        HAS_CRYPTO = True
    except ImportError:
        HAS_CRYPTO = False
        # Заглушка для отладки
        class Fernet:
            def __init__(self, key): self.key = key
            def encrypt(self, data): return data if isinstance(data, bytes) else data.encode()
            def decrypt(self, token): return token if isinstance(token, bytes) else token.encode()

class CryptoManager:
    """
    Единый интерфейс шифрования для ПК и Android.
    Автоматически выбирает бэкенд в зависимости от платформы.
    """
    
    def __init__(self, password: str):
        # Генерируем ключ из пароля (детерминированно)
        key = base64.urlsafe_b64encode(
            hashlib.sha256(password.encode()).digest()
        )
        
        if IS_ANDROID and not HAS_CRYPTO:
            # Android без simple-crypt: храним ключ как есть
            self._key = password.encode()
            self._mode = "fallback"
        elif IS_ANDROID:
            # Android с simple-crypt
            self._key = password.encode()
            self._mode = "simplecrypt"
        else:
            # ПК с cryptography
            self._fernet = Fernet(key)
            self._mode = "fernet"

    def encrypt(self, plaintext: str) -> str:
        """Шифрует строку → возвращает hex-строку (универсальный формат)"""
        if self._mode == "fernet":
            # cryptography.fernet возвращает bytes → base64
            return self._fernet.encrypt(plaintext.encode()).decode()
        elif self._mode == "simplecrypt":
            # simple-crypt возвращает bytes → hex для универсальности
            return sc_encrypt(self._key, plaintext).hex()
        else:
            # Fallback: без шифрования (для отладки)
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """Расшифровывает hex/base64 строку → возвращает исходный текст"""
        if self._mode == "fernet":
            # cryptography.fernet принимает base64-строку
            return self._fernet.decrypt(ciphertext.encode()).decode()
        elif self._mode == "simplecrypt":
            # simple-crypt принимает bytes → из hex
            try:
                return sc_decrypt(self._key, bytes.fromhex(ciphertext)).decode()
            except:
                # Если формат не hex (старое сообщение от ПК) — пробуем как base64
                try:
                    return sc_decrypt(self._key, base64.b64decode(ciphertext)).decode()
                except:
                    return "[⚠️ ОШИБКА РАСШИФРОВКИ]"
        else:
            # Fallback: без расшифровки
            return ciphertext

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Для файлов — возвращаем как есть (шифрование файлов вынесено отдельно)"""
        return data

    def decrypt_bytes(self, token: bytes) -> bytes:
        """Для файлов — возвращаем как есть"""
        return token