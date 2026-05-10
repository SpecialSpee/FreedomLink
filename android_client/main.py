# main.py — Android клиент на Kivy
# ✅ Использует те же client.py, database.py, encryption.py из pc_client/

import os
import sys
import json
import logging
from datetime import datetime

# Добавляем родительскую директорию в путь для импорта общих модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pc_client')))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window

from client import WSClient
from encryption import CryptoManager
from database import init_db, save_message, get_chat_history, init_global_chat_db, save_global_message, get_global_chat_history
from android_utils import get_db_path, get_vault_path, request_permissions

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

# 🎨 Кибер-социалистическая тема (упрощённая для Kivy)
THEME = {
    "bg": "#0a0a0a",
    "frame": "#1a1a1a",
    "accent": "#8a0303",
    "text": "#203f20",
    "text_white": "#ffffff"
}

class ChatUI(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.app = app
        self.current_user = ""
        self.current_contact = ""
        self.chat_mode = "private"
        
        # Инициализация
        self.crypto = CryptoManager("cyber_socialism_key_2026")
        self.network = WSClient(
            on_message=self._on_message,
            on_connect=self._on_connected
        )
        
        # UI элементы
        self._build_ui()
        
        # Инициализация БД с правильным путём
        init_db(get_db_path())
        init_global_chat_db(get_db_path())

    def _build_ui(self):
        # Заголовок
        header = Label(
            text="☭ FreedomLink Android",
            size_hint=(1, 0.1),
            color=(1, 0.2, 0.2, 1),
            bold=True
        )
        self.add_widget(header)
        
        # Область чата
        self.chat_scroll = ScrollView()
        self.chat_content = Label(
            text=">>> Выберите собеседника или переключитесь на глобальный чат <<<\n",
            size_hint_y=None,
            color=(0.125, 0.247, 0.125, 1),  # terminal green
            font_name='RobotoMono-Regular',
            halign='left',
            valign='top',
            text_size=(Window.width - 40, None)
        )
        self.chat_content.bind(texture_size=self.chat_content.setter('size'))
        self.chat_scroll.add_widget(self.chat_content)
        self.add_widget(self.chat_scroll)
        
        # Поле ввода
        input_row = BoxLayout(size_hint=(1, 0.15), padding=10, spacing=10)
        self.msg_input = TextInput(
            hint_text="Введите сообщение...",
            multiline=False,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(0.125, 0.247, 0.125, 1)
        )
        self.msg_input.bind(on_text_validate=lambda i: self._send())
        input_row.add_widget(self.msg_input)
        
        send_btn = Button(
            text="📡",
            size_hint=(0.2, 1),
            background_color=(0.54, 0.01, 0.01, 1),
            background_normal='',
            background_down='',
            color=(1, 1, 1, 1)
        )
        send_btn.bind(on_release=lambda b: self._send())
        input_row.add_widget(send_btn)
        self.add_widget(input_row)
        
        # Переключатель режима
        mode_row = BoxLayout(size_hint=(1, 0.08), padding=10, spacing=10)
        btn_private = Button(text="💬 Личный", background_color=(0.54, 0.01, 0.01, 1))
        btn_private.bind(on_release=lambda b: self._switch_mode("private"))
        btn_global = Button(text="🌍 Глобальный", background_color=(0.1, 0.1, 0.1, 1))
        btn_global.bind(on_release=lambda b: self._switch_mode("global"))
        mode_row.add_widget(btn_private)
        mode_row.add_widget(btn_global)
        self.add_widget(mode_row)
        
        # Статус
        self.status = Label(
            text="● ОФФЛАЙН",
            size_hint=(1, 0.07),
            color=(1, 0, 0, 1),
            bold=True
        )
        self.add_widget(self.status)

    def _switch_mode(self, mode):
        self.chat_mode = mode
        self.chat_content.text = ""
        if mode == "global":
            self._load_global_history()
        elif self.current_contact:
            self._load_history()

    def _on_connected(self):
        Clock.schedule_once(lambda dt: self._ui_connected(), 0)

    def _ui_connected(self):
        self.status.text = "● ОНЛАЙН"
        self.status.color = (0, 1, 0, 1)
        self.network.send(json.dumps({
            "type": "auth",
            "user_id": self.current_user,
            "password": self.app.password_hash
        }))
        self.network.send(json.dumps({"type": "request_users"}))

    def _on_message(self, raw_msg):
        Clock.schedule_once(lambda dt: self._handle_message(raw_msg), 0)

    def _handle_message(self, raw_msg):
        try:
            data = json.loads(raw_msg)
            msg_type = data.get("type")
            
            if msg_type == "chat":
                sender = data.get("sender")
                text = data.get("text")
                if data.get("encrypted"):
                    text = self.crypto.decrypt(text)
                self._append_chat(f"[{datetime.now().strftime('%H:%M')}] {sender}: {text}")
                
            elif msg_type == "global_chat":
                sender = data.get("sender")
                text = data.get("text")
                is_file = data.get("is_file", False)
                if is_file:
                    filename = data.get("filename")
                    size = data.get("size")
                    self._append_chat(f"[🌍] {sender} 📎 {filename} ({size} B)")
                else:
                    self._append_chat(f"[🌍 {datetime.now().strftime('%H:%M')}] {sender}: {text}")
                    
            elif msg_type == "users_list":
                # Можно добавить список контактов
                pass
                
        except Exception as e:
            logger.error(f"Message handler error: {e}")

    def _append_chat(self, text):
        self.chat_content.text += text + "\n"
        self.chat_scroll.scroll_to(self.chat_content)

    def _send(self):
        text = self.msg_input.text.strip()
        if not text:
            return
            
        if self.chat_mode == "global":
            payload = json.dumps({
                "type": "global_chat",
                "text": text,
                "is_file": False,
                "sender": self.current_user
            })
            self.network.send(payload)
            save_global_message(self.current_user, text, path=get_db_path())
        else:
            if not self.current_contact:
                return
            encrypted = self.crypto.encrypt(text)
            payload = json.dumps({
                "type": "chat",
                "sender": self.current_user,
                "receiver": self.current_contact,
                "text": encrypted,
                "encrypted": True
            })
            self.network.send(payload)
            save_message(self.current_user, self.current_contact, encrypted, path=get_db_path())
            self._append_chat(f"[{datetime.now().strftime('%H:%M')}] ВЫ: {text}")
        
        self.msg_input.text = ""

    def _load_history(self):
        if not self.current_contact:
            return
        history = get_chat_history(self.current_user, self.current_contact, path=get_db_path())
        self.chat_content.text = ""
        for sender, encrypted_text, ts in history:
            try:
                text = self.crypto.decrypt(encrypted_text)
            except:
                text = "[⚠️ ОШИБКА]"
            self._append_chat(f"[{ts}] {sender}: {text}")

    def _load_global_history(self):
        messages = get_global_chat_history(limit=50, path=get_db_path())
        self.chat_content.text = ">>> 🌍 ГЛОБАЛЬНЫЙ ЭФИР <<<\n"
        for msg in messages:
            if msg["is_file"]:
                self._append_chat(f"[🌍] {msg['sender']} 📎 {msg['filename']}")
            else:
                self._append_chat(f"[🌍] {msg['sender']}: {msg['text']}")


class FreedomLinkApp(App):
    def build(self):
        Window.clearcolor = (0.04, 0.04, 0.04, 1)
        self.password_hash = ""  # будет установлен после ввода
        self.ui = ChatUI(self)
        return self.ui

    def on_start(self):
        # Запрос разрешений на Android
        request_permissions()
        # Здесь можно показать диалог логина (упрощённо — хардкод для теста)
        self.ui.current_user = "ANDROID_USER"
        self.password_hash = "test_hash_placeholder"  # в реальном приложении — ввод пароля
        self.ui.network.connect("ws://193.242.106.52:8765")

    def on_stop(self):
        self.ui.network.disconnect()


if __name__ == '__main__':
    FreedomLinkApp().run()