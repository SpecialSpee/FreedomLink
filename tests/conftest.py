# tests/conftest.py
import pytest
import os
import tempfile
from encryption import CryptoManager

@pytest.fixture
def test_crypto():
    return CryptoManager("test_password_123")

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)