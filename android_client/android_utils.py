# android_utils.py — утилиты для Android-специфичных операций
import os
import platform

def get_storage_path() -> str:
    """Возвращает правильный путь для хранения данных"""
    if platform.system() == "Android":
        try:
            from android.storage import app_storage_path
            path = app_storage_path()
            os.makedirs(path, exist_ok=True)
            return path
        except ImportError:
            # Fallback для старых версий
            return "/sdcard/FreedomLink"
    return "."

def get_db_path() -> str:
    """Путь к базе данных"""
    return os.path.join(get_storage_path(), "chat_history.db")

def get_vault_path() -> str:
    """Путь к хранилищу файлов"""
    path = os.path.join(get_storage_path(), "vault")
    os.makedirs(path, exist_ok=True)
    return path

def request_permissions():
    """Запрашивает разрешения на Android (вызывать после инициализации Kivy)"""
    if platform.system() == "Android":
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])
        except ImportError:
            pass  # permissions уже могут быть в манифесте