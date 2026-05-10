from cryptography.fernet import Fernet
import base64
import hashlib

class CryptoManager:
    def __init__(self, password: str):
        self._key = base64.urlsafe_b64encode(
            hashlib.sha256(password.encode()).digest()
        )
        self._fernet = Fernet(self._key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, token: bytes) -> bytes:
        return self._fernet.decrypt(token)