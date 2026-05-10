# tests/test_crypto.py
def test_encrypt_decrypt(test_crypto):
    original = "Hello, World! 🔐"
    encrypted = test_crypto.encrypt(original)
    
    assert encrypted != original  # Зашифровано
    assert "gAAAAA" in encrypted  # Fernet-формат
    
    decrypted = test_crypto.decrypt(encrypted)
    assert decrypted == original

def test_different_encryptions(test_crypto):
    text = "Same text"
    enc1 = test_crypto.encrypt(text)
    enc2 = test_crypto.encrypt(text)
    
    # Fernet добавляет случайный IV — шифры разные
    assert enc1 != enc2
    assert test_crypto.decrypt(enc1) == text
    assert test_crypto.decrypt(enc2) == text