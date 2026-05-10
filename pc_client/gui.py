import os
import base64
import uuid
import tempfile
import platform
import json
import logging
import hashlib  # ✅ Для паролей
import shutil
import time
from pathlib import Path  # ✅ ДОБАВЛЕНО: для работы с путями тем
from tkinter import filedialog, messagebox
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from client import WSClient
from encryption import CryptoManager
from database import init_db, get_chat_history, save_message
from PIL import Image
import customtkinter as ctk

# 🎨 THEME MANAGER
class ThemeManager:
    def __init__(self, themes_dir="themes"):
        self.themes_dir = Path(themes_dir)
        self.themes = self._scan_themes()
        self.global_chat_cache: list = []
        
    def _scan_themes(self):
        themes = {}
        if self.themes_dir.exists():
            for theme_name in self.themes_dir.iterdir():
                if theme_name.is_dir():
                    config_file = theme_name / "config.json"
                    if config_file.exists():
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            config["path"] = theme_name
                            themes[theme_name.name] = config
        return themes
    
    def get_colors(self, theme_name):
        """Возвращает цвета темы (поддержка старого и нового формата)"""
        theme = self.themes.get(theme_name, {})
        # Новый формат: "appearance", старый: "colors"
        return theme.get("appearance", theme.get("colors", {}))
    
    def get_theme_names(self):
        return list(self.themes.keys())

# Глобальный экземпляр
theme_manager = ThemeManager()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# ⚙️ SETTINGS MANAGER
SETTINGS_FILE = "settings.json"

def load_settings() -> dict:
    """Загружает настройки из файла"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"last_theme": "cyber_socialism"}

def save_settings(settings: dict) -> None:
    """Сохраняет настройки в файл"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"⚠️ Failed to save settings: {e}")

# 🔴 КИБЕРСОЦИАЛИСТИЧЕСКАЯ ТЕМА
ctk.set_appearance_mode("dark")

# Кастомная цветовая схема: Красный + Чёрный + Зелёный терминал
CYBER_SOCIALISM_THEME = {
    "bg_color": "#0a0a0a",           # Глубокий чёрный
    "frame_color": "#1a1a1a",         # Тёмно-серый
    "accent_red": "#8a0303",          # Революционный красный
    "accent_orange": "#ff4500",       # Оранжевый неон
    "terminal_green": "#203f20",      # Зелёный терминал
    "text_primary": "#ffffff",        # Белый текст
    "text_secondary": "#8A8A8A",      # Серый текст
    "button_hover": "#880404",        # Тёмно-красный при наведении
}

ctk.set_default_color_theme("dark-blue")  # База, но переопределим цвета

class CyberSocialismApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 🎨 Загрузка темы (с учётом сохранённой)
        self.theme_manager = theme_manager
        settings = load_settings()
        self.current_theme_name = settings.get("last_theme", "cyber_socialism")
        
        # Если тема не найдена — фоллбек на дефолт
        if self.current_theme_name not in self.theme_manager.themes:
            self.current_theme_name = "cyber_socialism"
        
        self.apply_theme(self.current_theme_name)
        
        # 🚩 СОВЕТСКИЕ АТРИБУТЫ
        self.title("☭ FreedomLink | Съезд 1.7")
        self.geometry("900x650")
        self.configure(fg_color=self.theme_colors["bg_color"])
        # ... остальной код __init__ без изменений ...

        self.current_user = ""
        self.current_contact = ""
        self.crypto = CryptoManager("cyber_socialism_key_2026")
        # ☠️ Состояние для "Параноик-режима"
        self._liquidator_step = 0  # 0: Ожидание, 1: Долгое нажатие, 2: Клик 1, 3: ФИНАЛ
        self._press_start_time = 0
        self._long_press_threshold = 0.5  # Секунды
        self._animation_job = None  # Для анимации цвета
        self._is_pressing = False  # ✅ Флаг: кнопка сейчас нажата?
        self.network = WSClient(
            on_message=self._on_ws_message,
            on_connect=self._on_connected
        )
        
        # ✅ Кэш и защита от дублей для глобального чата
        self.global_chat_cache: list = []
        self._rendered_global_hashes: set = set()
        
        self._setup_ui()
        
        # 🔥 ПРИМЕНЯЕМ ЦВЕТА ТЕМЫ СРАЗУ ПОСЛЕ СОЗДАНИЯ UI
        self._refresh_ui_colors()

        # Синхронизируем селектор с загруженной темой
        if hasattr(self, 'theme_combobox'):
            self.theme_combobox.set(self.current_theme_name)

        # Эффект мигания курсора (как в терминале)
        self._blink_cursor()

    def _setup_ui(self):
        # Главный контейнер с сеткой
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ═════════════════════════════════════════
        # ЛЕВАЯ ПАНЕЛЬ (СОВЕТСКАЯ)
        # ═════════════════════════════════════════
        self.sidebar = ctk.CTkFrame(
            self, 
            width=250, 
            corner_radius=0,
            fg_color=CYBER_SOCIALISM_THEME["frame_color"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # ☭ ЛОГОТИП
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(20, 10), padx=10, fill="x")
        
        # Пытаемся загрузить кастомный логотип из темы
        logo_config = self.theme_manager.themes.get(self.current_theme_name, {})
        logo_file = logo_config.get("logo")
        
        if logo_file:
            logo_path = Path(self.theme_manager.themes[self.current_theme_name]["path"]) / logo_file
            if logo_path.exists():
                try:
                    logo_img = Image.open(logo_path)
                    logo_size = logo_config.get("logo_size", [96, 96])
                    logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
                    self.logo_image = ctk.CTkImage(logo_img, size=logo_size)
                    
                    ctk.CTkLabel(
                        logo_frame,
                        image=self.logo_image,
                        text=""
                    ).pack()
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load logo: {e}. Using fallback.")
                    # Fallback на текст
                    self._create_text_logo(logo_frame)
            else:
                self._create_text_logo(logo_frame)
        else:
            self._create_text_logo(logo_frame)
        
        # Разделитель
        ctk.CTkFrame(self.sidebar, height=2, fg_color=CYBER_SOCIALISM_THEME["accent_red"]).pack(pady=10, padx=10, fill="x")
        
        # 🔐 АВТОРИЗАЦИЯ ТОВАРИЩА
        ctk.CTkLabel(
            self.sidebar,
            text="ИДЕНТИФИКАЦИЯ ТОВАРИЩА:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CYBER_SOCIALISM_THEME["accent_orange"]
        ).pack(pady=(10, 5), padx=10, anchor="w")
        
        self.entry_user = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Введите позывной...",
            height=35,
            corner_radius=3,
            border_width=2,
            border_color=CYBER_SOCIALISM_THEME["accent_red"],
            fg_color="#0f0f0f",
            text_color=CYBER_SOCIALISM_THEME["terminal_green"]
        )
        self.entry_user.pack(pady=5, padx=10, fill="x")
        
        # 🔐 ПОЛЕ ПАРОЛЯ
        self.entry_pass = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Пароль доступа...",
            height=35,
            corner_radius=3,
            border_width=2,
            border_color=CYBER_SOCIALISM_THEME["accent_red"],
            fg_color="#0f0f0f",
            text_color=CYBER_SOCIALISM_THEME["terminal_green"],
            show="*"  # Маскируем ввод
        )
        self.entry_pass.pack(pady=5, padx=10, fill="x")

        self.btn_connect = ctk.CTkButton(
            self.sidebar,
            text="▶ ПОДКЛЮЧИТЬСЯ К СЕТИ",
            height=38,
            corner_radius=3,
            fg_color=CYBER_SOCIALISM_THEME["accent_red"],
            hover_color=CYBER_SOCIALISM_THEME["button_hover"],
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            # ❌ command убираем, используем свои обработчики
        )
        self.btn_connect.pack(pady=10, padx=10, fill="x")
        
        # ✅ Привязываем события мыши
        self.btn_connect.bind("<ButtonPress-1>", self._on_btn_connect_press)
        self.btn_connect.bind("<ButtonRelease-1>", self._on_btn_connect_release)
        self.btn_connect.bind("<Leave>", self._on_btn_connect_leave)  # Если ушли с кнопки
        
        # 🔌 КНОПКА "ОТКЛЮЧИТЬСЯ" (скрыта по умолчанию)
        self.btn_disconnect = ctk.CTkButton(
            self.sidebar,
            text="🔌 ОТКЛЮЧИТЬСЯ",
            height=38,
            corner_radius=3,
            fg_color="#cc0000",
            hover_color="#990000",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._disconnect,
            state="disabled"  # Скрыта пока не онлайн
        )
        self.btn_disconnect.pack(pady=5, padx=10, fill="x")

        # 🔑 Кнопка смены пароля (скрыта пока не онлайн)
        self.btn_change_pass = ctk.CTkButton(
            self.sidebar, text="🔑 СМЕНИТЬ ПАРОЛЬ", height=30,
            fg_color="#1a1a1a", hover_color=CYBER_SOCIALISM_THEME["accent_red"],
            text_color=CYBER_SOCIALISM_THEME["terminal_green"],
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._show_change_pass_dialog,
            state="disabled"
        )
        self.btn_change_pass.pack(pady=5, padx=10, fill="x")

        # 🎨 СЕЛЕКТОР ТЕМ
        ctk.CTkLabel(
            self.sidebar,
            text="🎨 ОФОРМЛЕНИЕ:",
            font=ctk.CTkFont(size=10),
            text_color=CYBER_SOCIALISM_THEME["text_secondary"]
        ).pack(pady=(15, 5), padx=10, anchor="w")
        
        theme_names = self.theme_manager.get_theme_names()
        self.theme_combobox = ctk.CTkComboBox(
            self.sidebar,
            values=theme_names,
            command=self._on_theme_selected,
            font=ctk.CTkFont(size=10)
        )
        self.theme_combobox.set("cyber_socialism")
        self.theme_combobox.pack(pady=5, padx=10, fill="x")

        # Разделитель
        ctk.CTkFrame(self.sidebar, height=2, fg_color=CYBER_SOCIALISM_THEME["accent_red"]).pack(pady=10, padx=10, fill="x")

        # 👥 АКТИВНЫЕ ТОВАРИЩИ В СЕТИ
        ctk.CTkLabel(
            self.sidebar,
            text="☭ АКТИВНЫЕ ТОВАРИЩИ:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=CYBER_SOCIALISM_THEME["terminal_green"]
        ).pack(pady=(10, 5), padx=10, anchor="w")
        
        self.contacts_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            width=230,
            height=300,
            corner_radius=3,
            fg_color="#0f0f0f",
            scrollbar_button_color=CYBER_SOCIALISM_THEME["accent_red"]
        )
        self.contacts_frame.pack(pady=5, padx=10, fill="both", expand=True)
        
        # Статусная строка
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="● ОФФЛАЙН",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#ff0000",
            fg_color="#1a0000",
            corner_radius=3
        )
        self.status_label.pack(pady=10, padx=10, fill="x")
        
        # ═════════════════════════════════════════
        # ПРАВАЯ ПАНЕЛЬ (ТЕРМИНАЛ)
        # ═════════════════════════════════════════
        self.chat_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=CYBER_SOCIALISM_THEME["frame_color"]
        )
        self.chat_frame.grid(row=0, column=1, sticky="nsew")
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Заголовок чата
        self.header_frame = ctk.CTkFrame(
            self.chat_frame,
            height=50,
            corner_radius=0,
            fg_color="#1a0000"
        )
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text="⚠ ВЫБЕРИТЕ ТОВАРИЩА ДЛЯ СВЯЗИ",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=CYBER_SOCIALISM_THEME["accent_orange"]
        )
        self.lbl_title.pack(pady=15, padx=20, side="left")
        
        # Область чата (терминальный стиль)
        self.txt_chat = ctk.CTkTextbox(
            self.chat_frame,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color="#050505",
            text_color=CYBER_SOCIALISM_THEME["terminal_green"],
            border_width=2,
            border_color=CYBER_SOCIALISM_THEME["accent_red"]
        )
        self.txt_chat.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        
        # Поле ввода
        self.input_frame = ctk.CTkFrame(
            self.chat_frame,
            height=70,
            corner_radius=0,
            fg_color="#1a1a1a"
        )
        self.input_frame.grid(row=2, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.entry_msg = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="ВВЕДИТЕ СООБЩЕНИЕ ДЛЯ ПЕРЕДАЧИ...",
            height=45,
            corner_radius=3,
            border_width=2,
            border_color=CYBER_SOCIALISM_THEME["accent_red"],
            fg_color="#0f0f0f",
            text_color=CYBER_SOCIALISM_THEME["terminal_green"],
            font=ctk.CTkFont(family="Courier New", size=11)
        )
        self.entry_msg.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        self.entry_msg.bind("<Return>", lambda e: self._send_message())
        
        self.btn_send = ctk.CTkButton(
            self.input_frame,
            text="📡 ОТПРАВИТЬ",
            width=140,
            height=45,
            corner_radius=3,
            fg_color=CYBER_SOCIALISM_THEME["accent_red"],
            hover_color=CYBER_SOCIALISM_THEME["button_hover"],
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._send_message,
            state="disabled"
        )
        self.btn_send.grid(row=0, column=1, padx=15, pady=15)

        # 📎 Кнопка прикрепления файла
        self.btn_attach = ctk.CTkButton(
            self.input_frame, text="📎", width=45, height=45,
            command=self._select_file, fg_color="#1a1a1a", hover_color="#333333",
            border_width=1, border_color=CYBER_SOCIALISM_THEME["accent_red"]
        )
        self.btn_attach.grid(row=0, column=2, padx=(0, 10), pady=15)
        
        # Сдвигаем кнопку отправки, чтобы влезла новая
        self.btn_send.grid(row=0, column=3, padx=15, pady=15)
        
        # Нижняя информационная панель
        info_frame = ctk.CTkFrame(self.chat_frame, height=30, corner_radius=0, fg_color="#0a0a0a")
        info_frame.grid(row=3, column=0, sticky="ew")
        
        ctk.CTkLabel(
            info_frame,
            text="🔐 ШИФРОВАНИЕ: AES-128 | СОЕДИНЕНИЕ: ЗАЩИЩЕНО | ВЕРСИЯ: 1.0.26",
            font=ctk.CTkFont(size=8),
            text_color=CYBER_SOCIALISM_THEME["text_secondary"]
        ).pack(pady=5)

        # 🌍 ПЕРЕКЛЮЧАТЕЛЬ: Личный / Глобальный чат
        self.chat_mode = "private"  # или "global"
        
        mode_frame = ctk.CTkFrame(self.chat_frame, height=40, fg_color="transparent")
        mode_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 0))
        
        self.btn_mode_private = ctk.CTkButton(
            mode_frame, text="💬 Личный", width=100, height=30,
            fg_color=CYBER_SOCIALISM_THEME["accent_red"],
            command=lambda: self._switch_chat_mode("private")
        )
        self.btn_mode_private.pack(side="left", padx=5)
        
        self.btn_mode_global = ctk.CTkButton(
            mode_frame, text="🌍 Глобальный", width=120, height=30,
            fg_color=CYBER_SOCIALISM_THEME.get("input_bg", "#1a1a1a"),  # ✅ Исправлено
            command=lambda: self._switch_chat_mode("global")
        )
        self.btn_mode_global.pack(side="left", padx=5)

    def _switch_chat_mode(self, mode: str):
        """Переключает между личным и глобальным чатом"""
        self.chat_mode = mode
        
        if mode == "private":
            self.btn_mode_private.configure(fg_color=self.theme_colors.get("accent_red", "#8a0303"))
            self.btn_mode_global.configure(fg_color=self.theme_colors.get("input_bg", "#1a1a1a"))
            if self.current_contact:
                self.lbl_title.configure(text=f"⚡ СВЯЗЬ С ТОВАРИЩЕМ {self.current_contact}")
                self._load_history()
            self.btn_send.configure(state="normal" if self.current_contact else "disabled")
        else:
            self.btn_mode_global.configure(fg_color=self.theme_colors.get("accent_red", "#8a0303"))
            self.btn_mode_private.configure(fg_color=self.theme_colors.get("input_bg", "#1a1a1a"))
            self.lbl_title.configure(text="🌍 ГЛОБАЛЬНЫЙ ЭФИР | Все видят все")
            # ✅ Кнопка ВСЕГДА активна в глобалке
            self.btn_send.configure(state="normal")
            self._load_global_history()

    def _load_global_history(self):
        """Загружает историю глобального чата"""
        self.txt_chat.configure(state="normal")
        self.txt_chat.delete("1.0", "end")
        self.txt_chat.insert("end", ">>> 🌍 ДОБРО ПОЖАЛОВАТЬ В ГЛОБАЛЬНЫЙ ЭФИР <<<\n")
        self.txt_chat.insert("end", ">>> Сообщения видны всем участникам <<<\n\n")
        
        # ✅ Показываем кэш сразу
        for msg in self.global_chat_cache:
            self._render_global_message(msg, is_history=True)
        
        # ✅ Запрашиваем свежие данные с сервера только если кэш пуст
        if not self.global_chat_cache:
            self.network.send(json.dumps({"type": "request_global_history"}))
        else:
            self.txt_chat.insert("end", "\n>>> ПОКАЗАН КЭШ (актуализация в фоне) <<<\n")
        
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")            

    def _create_text_logo(self, parent_frame):
        """Создаёт текстовый логотип (fallback)"""
        colors = self.theme_colors
        fonts = self.theme_fonts
        
        ctk.CTkLabel(
            parent_frame,
            text="☭",
            font=(fonts.get("title", "Segoe UI"), 48, "bold"),
            text_color=colors.get("accent_red", "#8a0303")
        ).pack()
        
        ctk.CTkLabel(
            parent_frame,
            text="FreedomLink v1.7",
            font=(fonts.get("title", "Segoe UI"), 18, "bold"),
            text_color=colors.get("terminal_green", "#203f20")
        ).pack()
        
        ctk.CTkLabel(
            parent_frame,
            text="СИСТЕМА СОЦИАЛЬНОЙ СВЯЗИ",
            font=(fonts.get("main", "Courier New"), fonts.get("size_small", 9)),
            text_color=colors.get("text_secondary", "#8A8A8A")
        ).pack()

    def _connect(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        
        if not username or not password:
            messagebox.showwarning("ВНИМАНИЕ", "ТОВАРИЩ, ЗАПОЛНИТЕ ПОЗЫВНОЙ И ПАРОЛЬ!")
            return
        
        self._reset_liquidator_ui()
        
        import hashlib
        # 🔐 Хешируем пароль ДО отправки (защита от sniffing)
        self.current_pass_hash = hashlib.sha256(password.encode()).hexdigest()
        self.current_user = username.upper()
        
        self.btn_connect.configure(state="disabled", text="⏳ ПОДКЛЮЧЕНИЕ...")
        self.network.connect("ws://193.242.106.52:8765")

    def _disconnect(self):
        """🔌 Корректное отключение от сети"""
        logger.info(f"[{self.current_user}] Отключение от сети...")
        
        # Закрываем соединение
        if self.network:
            self.network.disconnect() 
        
        # Очищаем UI
        self.current_user = ""
        self.current_contact = ""
        self.entry_user.configure(state="normal")
        self.entry_user.delete(0, "end")
        self.btn_connect.configure(state="normal", text="▶ ПОДКЛЮЧИТЬСЯ К СЕТИ")
        self.btn_disconnect.configure(state="disabled")
        self.status_label.configure(text="● ОФФЛАЙН", text_color="#ff0000", fg_color="#1a0000")
        self.title("☭ FreedomLink | Съезд 1.7")
        self.entry_pass.delete(0, "end")
        self.btn_change_pass.configure(state="disabled")

        # Очищаем список контактов
        for widget in self.contacts_frame.winfo_children():
            widget.destroy()
        
        # Очищаем чат
        self.txt_chat.configure(state="normal")
        self.txt_chat.delete("1.0", "end")
        self.txt_chat.insert("end", ">>> СОЕДИНЕНИЕ ЗАВЕРШЕНО <<<\n")
        self.txt_chat.configure(state="disabled")
        
        self.lbl_title.configure(text="⚠ ВЫБЕРИТЕ ТОВАРИЩА ДЛЯ СВЯЗИ")
        self.btn_send.configure(state="disabled")
        
        logger.info("✅ Отключено")

    def _on_connected(self):
        self.after(0, self._ui_connected)
        # ✅ Отправляем user_id + password_hash
        self.network.send(json.dumps({
            "type": "auth", 
            "user_id": self.current_user, 
            "password": self.current_pass_hash
        }))
        self.network.send(json.dumps({"type": "request_users"}))

    def _ui_connected(self):
        # Запрашиваем историю глобального чата при входе
        if self.chat_mode == "global":
            self.network.send(json.dumps({"type": "request_global_history"}))
        self.btn_connect.configure(state="disabled", text="✅ ПОДКЛЮЧЕНО")
        self.btn_disconnect.configure(state="normal")  # ✅ Показываем кнопку
        self.entry_user.configure(state="disabled")
        self.status_label.configure(text="● ОНЛАЙН", text_color="#00ff00", fg_color="#001a00")
        self.title(f"☭ КИБЕР-СВЯЗЬ | ТОВАРИЩ {self.current_user}")
        self.btn_change_pass.configure(state="normal")

    def _on_ws_message(self, raw_msg: str):
        if not self.current_user:
            return
        try:
            data = json.loads(raw_msg)
            msg_type = data.get("type")
            
            if msg_type == "chat":
                self.after(0, self._render_message, data)
            elif msg_type == "users_list":
                self.after(0, self._render_contacts, data.get("users", []))
            elif msg_type == "error":
                self.after(0, lambda: messagebox.showerror("СБОЙ СИСТЕМЫ", data.get("content", "ОШИБКА")))
            elif msg_type == "file_transfer":
                file_id = data.get("file_id")
                filename = data.get("filename")
                size = data.get("size")
                encoded_data = data.get("data")
                
                # 🔍 ОТЛАДКА
                logger.info(f"📥 Received file_transfer: {filename}, data_len={len(encoded_data) if encoded_data else 0}")
                
                if not encoded_data:
                    logger.error(f"❌ file_transfer missing 'data' field!")
                    messagebox.showerror("ОШИБКА", "Пустые данные файла")
                    return
                
                self.after(0, lambda: self._render_file_card(file_id, filename, size, is_sender=False))
                self._save_encrypted_file(file_id, encoded_data)

            elif msg_type == "success":  # ✅ НОВОЕ
                content = data.get("content", "")
                self.after(0, lambda: messagebox.showinfo("УСПЕХ", content))
                
                # ✅ Если сменили пароль — обновляем хеш в памяти GUI
                if "Password updated" in content and hasattr(self, '_pending_new_hash'):
                    self.current_pass_hash = self._pending_new_hash
                    self._pending_new_hash = None
                    logger.info("🔑 Client hash updated successfully.")
            elif msg_type == "global_file_data":
                # Получили файл от сервера по запросу
                file_id = data.get("file_id")
                filename = data.get("filename")
                encoded_data = data.get("data")
                
                if encoded_data:
                    try:
                        self._save_encrypted_file(file_id, encoded_data)
                        self._open_file(file_id, filename)
                        logger.info(f"📥 Received file from server: {filename}")
                    except Exception as e:
                        logger.error(f"File save error: {e}")
                        messagebox.showerror("ОШИБКА", "Не удалось сохранить файл")
                else:
                    messagebox.showerror("ОШИБКА", "Пустые данные файла")
                    
            elif msg_type == "global_chat":
                # ✅ Защита от дублей: РАЗНЫЙ хеш для текста и файлов
                if data.get("is_file"):
                    # Для файлов: хеш по sender + timestamp + file_id
                    msg_hash = f"{data.get('sender')}:{data.get('timestamp')}:{data.get('file_id')}"
                else:
                    # Для текста: хеш по sender + timestamp + текст
                    msg_hash = f"{data.get('sender')}:{data.get('timestamp')}:{data.get('text')[:30]}"
                
                if msg_hash not in self._rendered_global_hashes:
                    self._rendered_global_hashes.add(msg_hash)
                    self.global_chat_cache.append(data)
                    if len(self.global_chat_cache) > 200:
                        self.global_chat_cache = self.global_chat_cache[-200:]
                    self.after(0, self._render_global_message, data)
                
                # Очистка старых хешей
                if len(self._rendered_global_hashes) > 500:
                    self._rendered_global_hashes = set(list(self._rendered_global_hashes)[-300:])
            
            elif msg_type == "global_history":
                messages = data.get("messages", [])
                # ✅ Обновляем кэш и сбрасываем хеши
                self.global_chat_cache = messages
                self._rendered_global_hashes.clear()
                self.txt_chat.configure(state="normal")
                for msg in messages:
                    self._render_global_message(msg, is_history=True)
                self.txt_chat.insert("end", "\n>>> КОНЕЦ ИСТОРИИ <<<\n")
                self.txt_chat.see("end")
                self.txt_chat.configure(state="disabled")

        except Exception as e:
            logger.error(f"WS Handler error: {e}")

    def _download_global_file(self, file_id: str, filename: str):
        """Реальная загрузка файла из глобального чата"""
        # 1. Ищем файл в кэше
        for msg in self.global_chat_cache:
            if msg.get("file_id") == file_id and msg.get("is_file"):
                encoded_data = msg.get("data")
                if encoded_data:
                    try:
                        self._save_encrypted_file(file_id, encoded_data)
                        self._open_file(file_id, filename)
                        logger.info(f"📥 Downloaded global file: {filename}")
                        return
                    except Exception as e:
                        logger.error(f"Download error: {e}")
                        messagebox.showerror("ОШИБКА", "Не удалось сохранить файл")
                        return
        
        # 2. Если не в кэше — запрашиваем у сервера
        messagebox.showinfo("📥 Загрузка", "Файл не в кэше. Запрашиваем у сервера...")
        self.network.send(json.dumps({
            "type": "request_global_file",
            "file_id": file_id
        }))

    def _render_global_message(self, data: dict, is_history: bool = False):

        """Отрисовка сообщения глобального чата"""
        sender = data.get("sender", "НЕИЗВЕСТНО")
        text = data.get("text", "")
        timestamp = data.get("timestamp", "")
        is_file = data.get("is_file", False)
        
        # Форматируем время
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                ts = dt.strftime("%H:%M:%S")
            except:
                ts = timestamp[:8] if len(timestamp) > 8 else timestamp
        else:
            ts = datetime.now().strftime("%H:%M:%S")
        
        self.txt_chat.configure(state="normal")
        
        if is_file:
            # Карточка файла
            filename = data.get("filename", "unknown")
            size = data.get("size", 0)
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            file_id = data.get("file_id")
            
            self.txt_chat.insert("end", f"[{ts}] 🌍 {sender} 📎 ФАЙЛ: {filename} ({size_str})\n")
            
            # Кнопки (аналогично _render_file_card)
            import tkinter as tk
            textbox = getattr(self.txt_chat, '_textbox', None) or getattr(self.txt_chat, 'textbox', None)
            if textbox and file_id:
                btn_frame = tk.Frame(textbox, bg=self.theme_colors.get("bg_color", "#0a0a0a"), height=28)
                tk.Button(btn_frame, text="🔐 Скачать", command=lambda fid=file_id, fname=filename: self._download_global_file(fid, fname)).pack(side="left", padx=3)
                textbox.window_create("end", window=btn_frame)
                self.txt_chat.insert("end", "\n")
        else:
            # Обычное сообщение
            # Расшифровка если нужно (глобалка может быть без шифрования)
            if data.get("encrypted"):
                try:
                    text = self.crypto.decrypt(text)
                except:
                    text = "[⚠️ ОШИБКА РАСШИФРОВКИ]"
            
            self.txt_chat.insert("end", f"[{ts}] 🌍 {sender}: {text}\n")
        
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

    def _render_message(self, data: dict):
        sender = data.get("sender", "НЕИЗВЕСТНО")
        raw_text = data.get("text", "")
        text = self.crypto.decrypt(raw_text) if data.get("encrypted") else raw_text
        
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_chat.configure(state="normal")
        self.txt_chat.insert("end", f"[{ts}] {sender}: {text}\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

    def _render_contacts(self, users: list):
        # ✅ Если не онлайн — не обновляем контакты
        if not self.current_user:
            return
        # Очистка старого списка
        for widget in self.contacts_frame.winfo_children():
            widget.destroy()
        
        if not users:
            ctk.CTkLabel(
                self.contacts_frame,
                text="НЕТ АКТИВНЫХ ТОВАРИЩЕЙ",
                font=ctk.CTkFont(size=10),
                text_color=CYBER_SOCIALISM_THEME["text_secondary"]
            ).pack(pady=20, padx=10)
            return
        
        for user in users:
            if user == self.current_user:
                continue
            
            btn = ctk.CTkButton(
                self.contacts_frame,
                text=f"👤 {user}",
                height=40,
                corner_radius=3,
                fg_color="#1a1a1a",
                hover_color=CYBER_SOCIALISM_THEME["accent_red"],
                text_color=CYBER_SOCIALISM_THEME["terminal_green"],
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda u=user: self._select_contact(u),
                border_width=1,
                border_color=CYBER_SOCIALISM_THEME["accent_red"]
            )
            btn.pack(pady=3, padx=10, fill="x")

    def _select_contact(self, contact: str):
        self.current_contact = contact
        self.lbl_title.configure(text=f"⚡ СВЯЗЬ С ТОВАРИЩЕМ {contact}")
        self.btn_send.configure(state="normal")
        self._load_history()

    def _load_history(self):
        if not self.current_contact:
            return
        self.txt_chat.configure(state="normal")
        self.txt_chat.delete("1.0", "end")
        
        history = get_chat_history(self.current_user, self.current_contact)
        if not history:
            self.txt_chat.insert("end", ">>> ИСТОРИЯ ПЕРЕПИСКИ ОТСУТСТВУЕТ <<<\n")
        
        for sender, encrypted_text, ts in history:
            try:
                text = self.crypto.decrypt(encrypted_text)
            except Exception as e:
                logger.warning(f"Decrypt failed for message from {sender}: {e}")
                text = f"[⚠️ ОШИБКА РАСШИФРОВКИ] {encrypted_text[:50]}..."
            self.txt_chat.insert("end", f"[{ts}] {sender}: {text}\n")
            
        self.txt_chat.insert("end", "\n>>> КОНЕЦ ИСТОРИИ <<<\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

    def _send_message(self):
        text = self.entry_msg.get().strip()
        if not text:
            return
        
        if self.chat_mode == "global":
            # 🌍 Глобальная отправка — НЕ создаём хеш и НЕ отображаем заранее!
            payload = json.dumps({
                "type": "global_chat",
                "text": text,
                "is_file": False,
                "sender": self.current_user
                # ❌ НЕ отправляем timestamp — пусть сервер создаст
            })
            self.network.send(payload)
            # ✅ Ждём, пока сервер пришлёт сообщение обратно через global_chat
            # Тогда хеш совпадёт и дубля не будет
            
            if len(self.global_chat_cache) > 200:
                self.global_chat_cache = self.global_chat_cache[-200:]
        else:
            # 💬 Личная отправка
            if not self.current_contact:
                return
            try:
                encrypted = self.crypto.encrypt(text)
                payload = json.dumps({
                    "type": "chat",
                    "sender": self.current_user,
                    "receiver": self.current_contact,
                    "text": encrypted,
                    "encrypted": True
                })
            except Exception as e:
                logger.error(f"Encrypt failed: {e}")
                payload = json.dumps({
                    "type": "chat", "sender": self.current_user,
                    "receiver": self.current_contact, "text": text, "encrypted": False
                })
            self.network.send(payload)
            ts = datetime.now().strftime("%H:%M:%S")
            self.txt_chat.configure(state="normal")
            self.txt_chat.insert("end", f"[{ts}] ВЫ: {text}\n")
            self.txt_chat.see("end")
            self.txt_chat.configure(state="disabled")
            try:
                save_message(self.current_user, self.current_contact, self.crypto.encrypt(text))
            except:
                pass
        
        self.entry_msg.delete(0, "end")

    def _blink_cursor(self):
        # Эффект мигающего курсора (опционально)
        self.after(1000, self._blink_cursor)

    def _select_file(self):
        """Отправка файла: личный или глобальный чат"""
        
        # 🔍 ОТЛАДКА
        print("🔥🔥 _select_file ВЫЗВАН! 🔥🔥")
        logger.info(f"🔍 _select_file START: mode={self.chat_mode}, contact={self.current_contact}")
        
        filepath = filedialog.askopenfilename(
            title="Файл для глобального чата" if self.chat_mode == "global" else "Выбрать файл для передачи"
        )
        if not filepath:
            logger.info("❌ Файл не выбран")
            return

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        logger.info(f"📁 Выбран файл: {filename} ({file_size} bytes)")
        
        # Лимит: 10MB для глобалки, 200MB для личного
        MAX_SIZE = 10 * 1024 * 1024 if self.chat_mode == "global" else 200 * 1024 * 1024

        if file_size > MAX_SIZE:
            limit_mb = MAX_SIZE // 1024 // 1024
            logger.error(f"❌ Файл слишком большой: {file_size} > {MAX_SIZE}")
            messagebox.showwarning("ВНИМАНИЕ", f"Файл слишком большой!\nЛимит: {limit_mb} МБ")
            return

        try:
            logger.info(f"🔐 Чтение и шифрование файла...")
            # 🔐 ЧТЕНИЕ И ШИФРОВАНИЕ ФАЙЛА
            with open(filepath, "rb") as f:
                raw_data = f.read()

            encrypted_data = self.crypto.encrypt_bytes(raw_data)
            encoded_data = base64.b64encode(encrypted_data).decode("utf-8")
            file_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            logger.info(f"✅ Файл зашифрован: {len(encoded_data)} bytes")

            # 🌍 Глобальная отправка
            if self.chat_mode == "global":
                logger.info(f"🌍 Отправка в глобальный чат...")
                payload = json.dumps({
                    "type": "global_chat",
                    "is_file": True,
                    "file_id": file_id,
                    "filename": filename,
                    "size": file_size,
                    "data": encoded_data,
                    "sender": self.current_user,
                    "timestamp": timestamp
                })
                self.network.send(payload)
                logger.info(f"✅ [{self.current_user}] Global file sent: {filename}")
            
            # 💬 Личная отправка
            else:
                logger.info(f"💬 Отправка в личный чат...")
                logger.info(f"DEBUG: chat_mode={self.chat_mode}, current_contact={self.current_contact}")
                
                if not self.current_contact:
                    logger.error("❌ current_contact is empty!")
                    messagebox.showwarning("ВНИМАНИЕ", "Выберите собеседника для отправки файла")
                    return
                
                logger.info(f"✅ Отправка файла {filename} пользователю {self.current_contact}")
                
                payload = json.dumps({
                    "type": "file_transfer",
                    "file_id": file_id,
                    "filename": filename,
                    "size": file_size,
                    "receiver": self.current_contact,
                    "data": encoded_data
                })
                
                logger.info(f"📤 Отправка payload (size={len(payload)})...")
                self.network.send(payload)
                logger.info(f"✅ Payload отправлен")
                
                self._render_file_card(file_id, filename, file_size, is_sender=True)
                logger.info(f"✅ [{self.current_user}] Private file sent: {filename}")

        except Exception as e:
            logger.error(f"💥 File send error: {e}", exc_info=True)
            messagebox.showerror("ОШИБКА", f"Не удалось отправить файл:\n{e}")

    def _save_encrypted_file(self, file_id: str, encoded_data: str):
        if not encoded_data:
            logger.error("❌ _save_encrypted_file called with empty data")
            return
        print(f"[DEBUG] Сохраняю файл {file_id}, длина данных: {len(encoded_data) if encoded_data else 0}")  # ← ДОБАВЬ
        os.makedirs("./vault", exist_ok=True)
        filepath = f"./vault/{file_id}.enc"
        try:
            decoded = base64.b64decode(encoded_data)
            print(f"[DEBUG] После base64 decode: {len(decoded)} байт")  # ← ДОБАВЬ
            with open(filepath, "wb") as f:
                f.write(decoded)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            print(f"[DEBUG] ОШИБКА: {e}")  # ← ДОБАВЬ

    def _render_file_card(self, file_id: str, filename: str, size: int, is_sender: bool):
        self.txt_chat.configure(state="normal")
        
        size_str = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / 1024 / 1024:.1f} MB"
        
        # Текстовое описание
        self.txt_chat.insert("end", f"\n📎 ФАЙЛ: {filename} ({size_str})\n")
        
        # ✅ ИСПОЛЬЗУЕМ НАТИВНЫЕ TKINTER ВИДЖЕТЫ (не customtkinter!)
        import tkinter as tk
        
        # Безопасно получаем внутренний Text-виджет
        textbox = getattr(self.txt_chat, '_textbox', None) or getattr(self.txt_chat, 'textbox', None)
        
        if textbox:
            # Нативный tkinter Frame (можно встраивать!)
            btn_frame = tk.Frame(textbox, bg=CYBER_SOCIALISM_THEME["bg_color"], height=28)
            
            # Нативная кнопка "Открыть"
            tk.Button(
                btn_frame, text="🔐 Открыть",
                bg="#1a1a1a", fg=CYBER_SOCIALISM_THEME["terminal_green"],
                activebackground="#333333", activeforeground=CYBER_SOCIALISM_THEME["terminal_green"],
                relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
                font=("Courier New", 10, "bold"),
                command=lambda fid=file_id, fname=filename: self._open_file(fid, fname)
            ).pack(side="left", padx=3, pady=2)
            
            # Нативная кнопка "Удалить"
            tk.Button(
                btn_frame, text="🗑️ Удалить",
                bg="#1a1a1a", fg="#cc0000",
                activebackground="#333333", activeforeground="#cc0000",
                relief="flat", cursor="hand2", borderwidth=0, highlightthickness=0,
                font=("Courier New", 10, "bold"),
                command=lambda fid=file_id: self._delete_file(fid)
            ).pack(side="left", padx=3, pady=2)
            
            # Встраиваем tkinter-фрейм (это разрешено!)
            textbox.window_create("end", window=btn_frame)
        
        self.txt_chat.insert("end", "\n" + "-"*40 + "\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

    def _open_file(self, file_id: str, filename: str):
        filepath = f"./vault/{file_id}.enc"
        if not os.path.exists(filepath):
            messagebox.showwarning("ВНИМАНИЕ", "Файл не найден или уже уничтожен")
            return

        try:
            with open(filepath, "rb") as f:
                encrypted_data = f.read()
            
            print(f"[DEBUG] Читаю файл: {len(encrypted_data)} байт")  # ← ДОБАВЬ
            print(f"[DEBUG] Первые 50 байт: {encrypted_data[:50]}")  # ← ДОБАВЬ
            
            decrypted_data = self.crypto.decrypt_bytes(encrypted_data)

            # Создаем временный файл для открытия системной программой
            ext = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(decrypted_data)
                tmp_path = tmp.name
            
            # Запускаем стандартный просмотрщик
            if platform.system() == "Windows":
                os.startfile(tmp_path)
            elif platform.system() == "Darwin":
                os.system(f"open {tmp_path}")
            else:
                os.system(f"xdg-open {tmp_path}")
                
            logger.info(f"[{self.current_user}] Файл открыт: {filename}")
        except Exception as e:
            logger.error(f"Ошибка открытия: {e}")
            messagebox.showerror("ОШИБКА", "Не удалось расшифровать файл")

    def _delete_file(self, file_id: str):
        filepath = f"./vault/{file_id}.enc"
        if os.path.exists(filepath):
            try:
                # 🔥 Параноик-режим: перезапись нулями перед удалением
                size = os.path.getsize(filepath)
                with open(filepath, "r+b") as f:
                    f.write(b"\x00" * size)
                    f.flush()
                    os.fsync(f.fileno())
                os.remove(filepath)
                logger.info(f"[{self.current_user}] Файл уничтожен: {file_id}")
                messagebox.showinfo("УСПЕХ", "Файл безвозвратно стерт с диска")
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")
        else:
            messagebox.showwarning("ВНИМАНИЕ", "Файл уже отсутствует")

    # ☠️ АНИМАЦИЯ ЦВЕТА (плавное изменение)
    def _animate_button_fill(self, updates=50):
        """Визуальное заполнение кнопки с чётким сигналом активации"""
        # Вычисляем, на каком шаге сработает порог
        threshold_step = int((self._long_press_threshold * 1000) / (updates * 50) * updates)
        
        def _step(current):
            # Останавливаем, если анимация завершена или условия сброса
            if current >= updates or (not self._is_pressing and self._liquidator_step != 1):
                return
            
            progress = int((current / updates) * 100)
            filled = int(progress / 5)
            bar = "█" * filled + "░" * (20 - filled)
            
            # ✅ ВИЗУАЛЬНЫЙ ТРИГГЕР: когда достигнут порог
            if current >= threshold_step and self._liquidator_step == 0:
                # Резкая смена текста и цвета — сигнал ВНИМАНИЕ!»
                self.btn_connect.configure(
                    text=f"[{bar}] ✅ ВНИМАНИЕ ЧС!",
                    fg_color="#ff0000",      # Ярко-красный
                    hover_color="#ff0000",
                    text_color="#ffffff"
                )
            else:
                # Обычная анимация
                self.btn_connect.configure(
                    text=f"[{bar}] {progress}%",
                    fg_color="#cc0000" if current < threshold_step else "#ff0000",
                    hover_color="#cc0000" if current < threshold_step else "#ff0000"
                )
            
            self._animation_job = self.after(50, lambda: _step(current + 1))
        
        _step(0)

    # ☠️ ОБРАБОТЧИКИ КНОПКИ "ПАРАНОИК"
    def _on_btn_connect_press(self, event):
        """Начало нажатия"""
        self._press_start_time = time.time()
        self._is_pressing = True  # ✅ Новый флаг!
        self._animate_button_fill()  # Запускаем анимацию

    def _on_btn_connect_release(self, event):
        """Конец нажатия — определяем действие"""
        self._is_pressing = False
        duration = time.time() - self._press_start_time
        
        # === ШАГ 0: ОЖИДАНИЕ ===
        if self._liquidator_step == 0:
            if duration >= self._long_press_threshold:
                # ✅ Долгое нажатие сработало!
                self._liquidator_step = 1
                # Фиксируем визуальное состояние «вооружено»
                self.btn_connect.configure(
                    text="⚠️ РЕЖИМ АКТИВИРОВАН", 
                    fg_color="#ff0000", 
                    hover_color="#ff0000",
                    text_color="#ffffff"
                )
                logger.warning("☠️ Liquidator: ARMED (Step 1/3)")
            else:
                # ❌ Короткое нажатие — обычное подключение
                if not self.current_user:
                    self._connect()
                # Сбрасываем кнопку
                self._reset_liquidator_ui()
        
        # === ШАГ 1: ПОДТВЕРЖДЕНИЕ 1 ===
        elif self._liquidator_step == 1:
            self._liquidator_step = 2
            self.btn_connect.configure(
                text="☠️ ПОДТВЕРДИТЕ ЗАЧИСТКУ", 
                fg_color="#000000", 
                hover_color="#330000",
                text_color="#ff0000"
            )
            logger.warning("☠️ Liquidator: Step 2/3")
            
        # === ШАГ 2: ФИНАЛ ===
        elif self._liquidator_step == 2:
            self._execute_liquidator()
            self._liquidator_step = 0

    def _on_btn_connect_leave(self, event):
        """Если курсор ушёл с кнопки во время нажатия — сброс"""
        if self._liquidator_step == 0 and self._is_pressing:
            self._is_pressing = False
            if self._animation_job:
                self.after_cancel(self._animation_job)
                self._animation_job = None
            self._reset_liquidator_ui()

    def _reset_liquidator_ui(self):
        """Сброс кнопки в исходное состояние"""
        self._liquidator_step = 0
        if self._animation_job:
            self.after_cancel(self._animation_job)
            self._animation_job = None
        self.btn_connect.configure(
            text="▶ ПОДКЛЮЧИТЬСЯ К СЕТИ",
            fg_color=CYBER_SOCIALISM_THEME["accent_red"],
            hover_color=CYBER_SOCIALISM_THEME["button_hover"],
            text_color="white",
            state="normal"
        )

    def _execute_liquidator(self):
        """🔥 ПОЛНАЯ ЗАЧИСТКА ДАННЫХ"""
        logger.critical("☠️ EXECUTING LIQUIDATOR PROTOCOL...")
        
        # 1. Визуальный эффект
        self._liquidator_step = 3  # Блокируем повторные нажатия
        self.btn_connect.configure(text="💥 УНИЧТОЖЕНИЕ...", fg_color="#000000")
        self.update()
        
        try:
            # 2. Уничтожение папки vault
            vault_path = "./vault"
            if os.path.exists(vault_path):
                logger.info("🔥 Wiping vault directory...")
                for root, dirs, files in os.walk(vault_path, topdown=False):
                    for name in files:
                        filepath = os.path.join(root, name)
                        size = os.path.getsize(filepath)
                        with open(filepath, "r+b") as f:
                            f.write(b"\x00" * size)
                        os.remove(filepath)
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(vault_path)
                logger.info("✅ Vault destroyed.")

            # 3. Уничтожение БД
            db_path = "chat_history.db"
            if os.path.exists(db_path):
                logger.info("🔥 Deleting database...")
                size = os.path.getsize(db_path)
                with open(db_path, "r+b") as f:
                    f.write(b"\x00" * size)
                os.remove(db_path)
                logger.info("✅ Database destroyed.")
                
        except Exception as e:
            logger.error(f"💥 Liquidator Error: {e}")
        
        # 4. Финал
        #logger.critical("☠️ SYSTEM PURGED.")
        #messagebox.showwarning("ПРОТОКОЛ ЗАВЕРШЕН", "✅ ВСЕ ДАННЫЕ УНИЧТОЖЕНЫ.\n🔒 СВЯЗЬ ОБОРВАНА.")
        self.destroy()

    def _show_change_pass_dialog(self):
        """Окно смены пароля — чистая версия"""
        dialog = tk.Toplevel(self)
        dialog.title("Смена пароля")
        dialog.geometry("320x210")
        dialog.configure(bg=CYBER_SOCIALISM_THEME["bg_color"])
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Текущий пароль:", bg=CYBER_SOCIALISM_THEME["bg_color"], 
                 fg=CYBER_SOCIALISM_THEME["terminal_green"], font=("Segoe UI", 10)).pack(pady=(15,2))
        old_entry = tk.Entry(dialog, show="*", fg=CYBER_SOCIALISM_THEME["terminal_green"], bg="#0f0f0f")
        old_entry.pack(pady=2, padx=25, fill="x")

        tk.Label(dialog, text="Новый пароль:", bg=CYBER_SOCIALISM_THEME["bg_color"], 
                 fg=CYBER_SOCIALISM_THEME["terminal_green"], font=("Segoe UI", 10)).pack(pady=(10,2))
        new_entry = tk.Entry(dialog, show="*", fg=CYBER_SOCIALISM_THEME["terminal_green"], bg="#0f0f0f")
        new_entry.pack(pady=2, padx=25, fill="x")

        def confirm():
            old_pwd = old_entry.get().strip()
            new_pwd = new_entry.get().strip()
            if not old_pwd or not new_pwd:
                messagebox.showwarning("ВНИМАНИЕ", "Заполните оба поля!")
                return
            if old_pwd == new_pwd:
                messagebox.showwarning("ВНИМАНИЕ", "Новый пароль должен отличаться!")
                return

            old_hash = hashlib.sha256(old_pwd.encode()).hexdigest()
            new_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
            
            # Сохраняем хеш для обновления после ответа сервера
            self._pending_new_hash = new_hash
            
            payload = json.dumps({
                "type": "change_password",
                "old_password": old_hash,
                "new_password": new_hash
            })
            self.network.send(payload)
            logger.info(f"[{self.current_user}] Sent password change request.")
            
            dialog.destroy()
            messagebox.showinfo("ОТПРАВЛЕНО", "Запрос отправлен.\nОжидайте ответа сервера...")

        tk.Button(dialog, text="✅ ПОДТВЕРДИТЬ СМЕНУ", bg=CYBER_SOCIALISM_THEME["accent_red"], fg="white",
                  font=("Segoe UI", 10, "bold"), activebackground="#660000", command=confirm).pack(pady=20)

    def _on_theme_selected(self, theme_name):
        """Обработчик выбора темы + авто-сохранение"""
        self.apply_theme(theme_name)
        self._refresh_ui_colors()
        
        # 💾 Сохраняем выбор
        settings = load_settings()
        settings["last_theme"] = theme_name
        save_settings(settings)
        
        logger.info(f"🎨 Theme changed to: {theme_name} (saved)")

    def apply_theme(self, theme_name):
        """Применяет тему: обновляет цвета и перекрашивает UI"""
        if theme_name not in self.theme_manager.themes:
            return
        
        self.current_theme_name = theme_name
        theme_config = self.theme_manager.themes[theme_name]
        
        # Получаем параметры из нового формата конфиг-файла
        self.theme_colors = theme_config.get("appearance", theme_config.get("colors", {}))
        self.theme_shapes = theme_config.get("shapes", {})
        self.theme_fonts = theme_config.get("fonts", {})
        
        # Обновляем глобальную переменную для совместимости
        global CYBER_SOCIALISM_THEME
        CYBER_SOCIALISM_THEME.update(self.theme_colors)
        
        # Перекрашиваем интерфейс
        self._refresh_ui_colors()
        logger.info(f"🎨 Theme applied: {theme_name}")
    
    def _refresh_ui_colors(self):
        """Перекрашивает ВСЕ виджеты по параметрам текущей темы"""
        colors = getattr(self, 'theme_colors', CYBER_SOCIALISM_THEME)
        shapes = getattr(self, 'theme_shapes', {})
        fonts = getattr(self, 'theme_fonts', {})
        
        # === ГЛАВНОЕ ОКНО ===
        self.configure(fg_color=colors.get("bg_color", "#0a0a0a"))
        
        # === ЛЕВАЯ ПАНЕЛЬ ===
        if hasattr(self, 'sidebar'):
            self.sidebar.configure(
                fg_color=colors.get("sidebar_color", colors.get("frame_color", "#1a1a1a"))
            )
        
        # === ПОЛЯ ВВОДА ===
        for entry in [getattr(self, 'entry_user', None), getattr(self, 'entry_pass', None), getattr(self, 'entry_msg', None)]:
            if entry:
                entry.configure(
                    fg_color=colors.get("input_bg", "#0f0f0f"),
                    text_color=colors.get("terminal_green", "#203f20"),
                    border_color=colors.get("border_color", "#8a0303"),
                    corner_radius=shapes.get("button_corner_radius", 3)
                )
        
        # === КНОПКИ ===
        buttons = [
            getattr(self, 'btn_connect', None),
            getattr(self, 'btn_disconnect', None),
            getattr(self, 'btn_change_pass', None),
            getattr(self, 'btn_send', None),
            getattr(self, 'btn_attach', None)
        ]
        for btn in buttons:
            if btn:
                btn.configure(
                    fg_color=colors.get("accent_red", "#8a0303"),
                    hover_color=colors.get("button_hover", "#880404"),
                    corner_radius=shapes.get("button_corner_radius", 3),
                    height=shapes.get("button_height", 38)
                )
        
        # === ЧАТ И ФРЕЙМЫ ===
        if hasattr(self, 'chat_frame'):
            self.chat_frame.configure(fg_color=colors.get("frame_color", "#1a1a1a"))
        if hasattr(self, 'header_frame'):
            self.header_frame.configure(fg_color=colors.get("header_bg", "#1a0000"))
        if hasattr(self, 'input_frame'):
            self.input_frame.configure(fg_color=colors.get("sidebar_color", "#1a1a1a"))
        if hasattr(self, 'contacts_frame'):
            self.contacts_frame.configure(
                fg_color=colors.get("input_bg", "#0f0f0f"),
                scrollbar_button_color=colors.get("accent_red", "#8a0303")
            )
        
        # === ОБЛАСТЬ ЧАТА ===
        if hasattr(self, 'txt_chat'):
            self.txt_chat.configure(
                fg_color=colors.get("input_bg", "#050505"),
                text_color=colors.get("terminal_green", "#203f20"),
                border_color=colors.get("border_color", "#8a0303")
            )
        
        # === СТАТУС И ЗАГОЛОВКИ ===
        if hasattr(self, 'status_label'):
            self.status_label.configure(
                fg_color="#1a0000",
                text_color="#ff0000" if "ОФФЛАЙН" in self.status_label.cget("text") else "#00ff00"
            )
        if hasattr(self, 'lbl_title'):
            self.lbl_title.configure(text_color=colors.get("accent_orange", "#ff4500"))
        
        # === СЕЛЕКТОР ТЕМ ===
        if hasattr(self, 'theme_combobox'):
            self.theme_combobox.configure(
                fg_color=colors.get("input_bg", "#0f0f0f"),
                border_color=colors.get("border_color", "#8a0303"),
                text_color=colors.get("text_primary", "#ffffff")
            )
        
        # === ПЕРЕРАЗРИСОВКА КОНТАКТОВ ===
        if hasattr(self, 'contacts_frame'):
            for widget in self.contacts_frame.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    widget.configure(
                        fg_color=colors.get("input_bg", "#1a1a1a"),
                        hover_color=colors.get("accent_red", "#8a0303"),
                        text_color=colors.get("terminal_green", "#203f20"),
                        border_color=colors.get("border_color", "#8a0303")
                    )

        # === ОБНОВЛЕНИЕ ЛОГОТИПА ===
        # Пересоздаём логотип при смене темы
        if hasattr(self, 'sidebar'):
            # Находим logo_frame и пересоздаём
            for widget in self.sidebar.winfo_children():
                if isinstance(widget, ctk.CTkFrame) and widget.cget("fg_color") == "transparent":
                    # Очищаем старый логотип
                    for child in widget.winfo_children():
                        child.destroy()
                    # Создаём новый
                    self._create_logo_in_frame(widget)
                    break
    
    def _create_logo_in_frame(self, parent_frame):
        """Создаёт логотип в указанном фрейме (для смены тем)"""
        logo_config = self.theme_manager.themes.get(self.current_theme_name, {})
        logo_file = logo_config.get("logo")
        colors = self.theme_colors
        fonts = self.theme_fonts
        
        if logo_file:
            logo_path = Path(self.theme_manager.themes[self.current_theme_name]["path"]) / logo_file
            if logo_path.exists():
                try:
                    logo_img = Image.open(logo_path)
                    logo_size = logo_config.get("logo_size", [96, 96])
                    logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
                    self.logo_image = ctk.CTkImage(logo_img, size=logo_size)
                    
                    ctk.CTkLabel(
                        parent_frame,
                        image=self.logo_image,
                        text=""
                    ).pack()
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load logo: {e}")
        
        # Fallback на текст
        self._create_text_logo(parent_frame)

        self.update()


if __name__ == "__main__":
    app = CyberSocialismApp()
    app.mainloop()
