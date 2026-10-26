#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lura — мила ШІ-агентка для ПК (Windows / Linux / macOS).

Встановлення:  pip install -r requirements.txt
               (PyQt6-WebEngine потрібен для анімацій OpenLura)
Запуск:        python lura.py

Налаштування — шестерня в шапці (відкриваються всередині вікна, з плавним переходом).
Локально: llama.cpp (запускається сам, без вікна консолі, статус — внизу чату) або LM Studio.
Дані: ~/.lura  (config.json, memory.json, reminders.json, history.json, games/, fonts/, emoji/, ping.wav)
"""
import sys, os, re, json, time, math, random, base64, subprocess, shutil, threading, difflib, wave, struct, shlex
import html as htmlmod, datetime as dt, webbrowser, fnmatch, platform
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
import requests
from PyQt6.QtCore import (Qt, QTimer, QPointF, QRectF, QRect, QPoint, QSize, QUrl, QThread, pyqtSignal, QObject,
                          QPropertyAnimation, QEasingCurve, QBuffer, QIODevice, pyqtProperty)
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient, QPainterPath,
                         QCursor, QFont, QFontMetrics, QGuiApplication, QIcon, QPixmap, QImage, QFontDatabase)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
                             QPlainTextEdit, QScrollArea, QSizePolicy, QGraphicsOpacityEffect, QLineEdit,
                             QSystemTrayIcon, QMenu, QFileDialog, QMessageBox, QComboBox, QSlider, QSpinBox, QAbstractSpinBox,
                             QDialog, QCompleter)
try: from PyQt6.QtMultimedia import QSoundEffect
except Exception: QSoundEffect = None
try: from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception: QWebEngineView = None

IS_WIN, IS_MAC = sys.platform.startswith("win"), sys.platform == "darwin"
HOME = Path.home() / ".lura"; HOME.mkdir(exist_ok=True)
CFG_P, MEM_P, HIST_P, REM_P, PING_P, CHATS_P = (HOME / n for n in ("config.json", "memory.json", "history.json", "reminders.json", "ping.wav", "chats.json"))
EMO_DIR, FONT_DIR = HOME / "emoji", HOME / "fonts"; EMO_DIR.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Lura)"}
FACE_CY = 108           # центр мордашки нижче кнопок верхньої панелі
PW, PH = 104, 44        # розмір «віконечка» з мордашкою (компактний режим)
ORB_SIZE = 84           # кружечок завжди одного розміру
MENU_W = 340            # ширина колонки меню (календар/нагадування/чати) при розширенні вікна
GRIP = 34               # трикутник зміни розміру
MIN_W, MIN_H, MAX_W, MAX_H = 290, 300, 760, 1100
LANG = "en"
LANG_NAMES = {"en": "English", "uk": "Ukrainian", "ru": "Russian"}
TRANSLATIONS = {
"Прикріпити файл": {"en":"Attach a file", "ru":"Прикрепить файл"},
"Відпусти файли тут, щоб прикріпити": {"en":"Drop files here to attach", "ru":"Отпусти файлы здесь, чтобы прикрепить"},
"поклади файл шрифту (.ttf) поруч із lura.py": {"en":"put a font file (.ttf) next to lura.py or drop it on the window", "ru":"положи файл шрифта (.ttf) рядом с lura.py или перетащи его в окно"},
"шрифт змінено": {"en":"font changed", "ru":"шрифт изменён"}, "не вдалося прочитати шрифт": {"en":"could not read the font file", "ru":"не удалось прочитать шрифт"},
"Відпусти файл шрифту тут": {"en":"Drop the font file here", "ru":"Отпусти файл шрифта здесь"}, "Меню": {"en":"Menu", "ru":"Меню"},
"Модель": {"en":"Model", "ru":"Модель"}, "Лура": {"en":"Lura", "ru":"Лура"},
"Локальна": {"en":"Local", "ru":"Локальная"}, "Ключ OpenRouter": {"en":"OpenRouter API key", "ru":"Ключ OpenRouter"},
"Який локальний сервер": {"en":"Local server", "ru":"Локальный сервер"}, "Файл llama-server": {"en":"llama-server executable", "ru":"Файл llama-server"},
"Модель (.gguf)": {"en":"Model (.gguf)", "ru":"Модель (.gguf)"}, "Порт": {"en":"Port", "ru":"Порт"},
"Контекст (токенів)": {"en":"Context (tokens)", "ru":"Контекст (токенов)"}, "Шарів на GPU (-ngl)": {"en":"GPU layers (-ngl)", "ru":"Слоёв на GPU (-ngl)"},
"Додаткові аргументи": {"en":"Additional arguments", "ru":"Дополнительные аргументы"}, "Запускати сервер автоматично": {"en":"Start server automatically", "ru":"Запускать сервер автоматически"},
"Сервер стартує сам, коли обираєш «Локальна», без вікна консолі. Прогрес — внизу чату.": {"en":"The server starts when you select Local, without a console window. Progress appears at the bottom of the chat.", "ru":"Сервер запускается при выборе «Локальная» без окна консоли. Прогресс отображается внизу чата."},
"Адреса LM Studio": {"en":"LM Studio address", "ru":"Адрес LM Studio"}, "Назва моделі (необов'язково)": {"en":"Model name (optional)", "ru":"Название модели (необязательно)"},
"Як тебе звати": {"en":"Your name", "ru":"Как тебя зовут"}, "Бачити екран (потрібна vision-модель)": {"en":"See the screen (requires a vision model)", "ru":"Видеть экран (нужна vision-модель)"},
"Питати дозволу на небезпечні дії": {"en":"Ask before risky actions", "ru":"Спрашивать разрешение на опасные действия"}, "Може писати першою": {"en":"May message first", "ru":"Может писать первой"},
"Звук повідомлень (коли згорнута)": {"en":"Message sound (when minimized)", "ru":"Звук сообщений (когда свёрнута)"}, "Пише першою раз на, хв:": {"en":"Message first every, min:", "ru":"Пишет первой раз в, мин:"},
"Папка з ярликами (ігри, програми)": {"en":"Shortcuts folder (games, apps)", "ru":"Папка с ярлыками (игры, программы)"}, "Команди, які можна без питань": {"en":"Commands allowed without asking", "ru":"Команды, разрешённые без вопросов"},
"Одна команда на рядок. * — будь-що. Команди з ; & | > завжди питають.": {"en":"One command per line. * means anything. Commands containing ; & | > always require confirmation.", "ru":"Одна команда на строку. * — что угодно. Команды с ; & | > всегда требуют подтверждения."},
"Вигляд": {"en":"Appearance", "ru":"Внешний вид"}, "Темна": {"en":"Dark", "ru":"Тёмная"}, "Світла": {"en":"Light", "ru":"Светлая"},
"Тема": {"en":"Theme", "ru":"Тема"}, "Емодзі": {"en":"Emoji", "ru":"Эмодзи"}, "Шрифт (з папки поруч зі скриптом, після перезапуску)": {"en":"Font (after restart)", "ru":"Шрифт (после перезапуска)"}, "Готово": {"en":"Done", "ru":"Готово"},
"Напиши мені…": {"en":"Write to me…", "ru":"Напиши мне…"}, "Налаштування": {"en":"Settings", "ru":"Настройки"}, "Вийти": {"en":"Quit", "ru":"Выход"},
"Згорнути / розгорнути": {"en":"Minimize / expand", "ru":"Свернуть / развернуть"}, "Розмір кружечка": {"en":"Orb size", "ru":"Размер кружка"}, "Менший": {"en":"Smaller", "ru":"Меньше"}, "Більший": {"en":"Larger", "ru":"Больше"},
"Світла / темна тема": {"en":"Light / dark theme", "ru":"Светлая / тёмная тема"}, "думаю…": {"en":"Thinking…", "ru":"Думаю…"}, "зачекай, я ще думаю…": {"en":"One moment, I’m still thinking…", "ru":"Подожди, я ещё думаю…"},
"Мова": {"en":"Language", "ru":"Язык"}, "Локально": {"en":"Local", "ru":"Локально"},
"Назад до чату": {"en":"Back to chat", "ru":"Назад в чат"}, "Згорнути в кружечок": {"en":"Minimize to orb", "ru":"Свернуть в кружок"},
"Показати Лурі екран разом із повідомленням": {"en":"Share screen with message", "ru":"Показать Луре экран вместе с сообщением"},
"OpenRouter": {"en":"OpenRouter", "ru":"OpenRouter"}, "llama.cpp": {"en":"llama.cpp", "ru":"llama.cpp"}, "LM Studio": {"en":"LM Studio", "ru":"LM Studio"},
"Привіт! Я Лура. Мордашка реагує на твої слова й без моделі. Щоб я могла відповідати текстом, під'єднай OpenRouter, Google Gemini з файлом keys.txt або локальну модель.": {"en":"Hi! I'm Lura. My face reacts to your words even without a model. To chat with me, connect OpenRouter, Google Gemini with keys.txt, or a local model.", "ru":"Привет! Я Лура. Моё лицо реагирует на твои слова даже без модели. Чтобы я могла отвечать текстом, подключи OpenRouter, Google Gemini с файлом keys.txt или локальную модель."},
"Я відреагувала настрієм офлайн. Для текстової відповіді під'єднай модель у налаштуваннях.": {"en":"I reacted offline. Connect a model in Settings to get text replies.", "ru":"Я отреагировала офлайн. Подключи модель в настройках, чтобы получать текстовые ответы."},
"завантажую шрифт…": {"en":"Downloading font…", "ru":"Загружаю шрифт…"}, "не вдалося зареєструвати шрифт": {"en":"Could not register font", "ru":"Не удалось зарегистрировать шрифт"}, "не вдалось завантажити шрифт": {"en":"Could not download font", "ru":"Не удалось загрузить шрифт"},
"Ім'я": {"en":"Name", "ru":"Имя"}, "Запускати сервер автоматично": {"en":"Start server automatically", "ru":"Запускать сервер автоматически"},
"--flash-attn -t 8": {"en":"--flash-attn -t 8", "ru":"--flash-attn -t 8"}, "Показати Лурі екран разом із повідомленням": {"en":"Share screen with message", "ru":"Показать Луре экран вместе с сообщением"}}
TRANSLATIONS.update({
    "API-хмара": {"en": "API cloud", "ru": "API-облако"},
    "Ключ Google API": {"en": "Google API key", "ru": "Ключ Google API"},
    "Файл ключів Google (необов'язково, один ключ на рядок)": {"en": "Google keys file (optional, one key per line)", "ru": "Файл ключей Google (необязательно, один ключ на строку)"},
    "Модель Google Gemini": {"en": "Google Gemini model", "ru": "Модель Google Gemini"},
    "Ключ із поля та keys.txt використовуються по черзі. Весь контекст діалогу передається з кожним запитом.": {"en": "The key in this field and keys.txt are rotated. The full conversation context is sent with each request.", "ru": "Ключ из этого поля и keys.txt используются по очереди. Весь контекст диалога отправляется с каждым запросом."},
    "Vision-модель (.gguf), не обов'язково": {"en": "Vision model (.gguf), optional", "ru": "Vision-модель (.gguf), не обязательно"},
    "Не обов'язково: окрема модель, що вміє бачити скріншоти. Порожньо — екран бачить основна модель.": {"en": "Optional: a separate model that can see screenshots. If empty, the main model sees the screen.", "ru": "Не обязательно: отдельная модель, умеющая видеть скриншоты. Если пусто, экран видит основная модель."},
    "Назва vision-моделі (не обов'язково)": {"en": "Vision model name (optional)", "ru": "Название vision-модели (не обязательно)"},
    "Не обов'язково: модель LM Studio, що розуміє зображення (для скріншотів). Порожньо — основна.": {"en": "Optional: an LM Studio model that understands images (for screenshots). If empty, the main one is used.", "ru": "Не обязательно: модель LM Studio, понимающая изображения (для скриншотов). Если пусто — основная."},
    "Модель LM Studio (не обов'язково)": {"en": "LM Studio model (optional)", "ru": "Модель LM Studio (не обязательно)"},
    "Не обов'язково: сервер LM Studio і ця модель запускатимуться самі. Порожньо — модель, що вже завантажена в LM Studio.": {"en": "Optional: the LM Studio server and this model start automatically. If empty, the model already loaded in LM Studio is used.", "ru": "Не обязательно: сервер LM Studio и эта модель запускаются сами. Если пусто — модель, уже загруженная в LM Studio."},
    "Характер": {"en": "Character", "ru": "Характер"},
    "Стримана": {"en": "Restrained", "ru": "Сдержанная"},
    "Жива": {"en": "Lively", "ru": "Живая"},
    "Ярка": {"en": "Bright", "ru": "Яркая"},
    "Сарказм: легкі підколи": {"en": "Sarcasm: light teasing", "ru": "Сарказм: лёгкие подколы"},
    "Може обиджатися на грубість": {"en": "May take offense at rudeness", "ru": "Может обижаться на грубость"},
    "Поведінка": {"en": "Behavior", "ru": "Поведение"},
    "Новий чат": {"en": "New chat", "ru": "Новый чат"},
    "Очистити чат": {"en": "Clear chat", "ru": "Очистить чат"},
    "Видалити чат": {"en": "Delete chat", "ru": "Удалить чат"},
    "Чати": {"en": "Chats", "ru": "Чаты"},
    "Пам'ять — павутина": {"en": "Memory — web", "ru": "Память — паутина"},
    "Меню — календар і чати": {"en": "Menu — calendar & chats", "ru": "Меню — календарь и чаты"},
    "Факти": {"en": "Facts", "ru": "Факты"},
    "Побажання": {"en": "Wishes", "ru": "Пожелания"},
    "клікни по вузлику, щоб прочитати спогад": {"en": "click a node to read the memory", "ru": "нажми на узелок, чтобы прочитать воспоминание"},
    "LM Studio не запущено — запусти сервер у LM Studio (вкладка Developer)": {"en": "LM Studio is not running — start the server in LM Studio (Developer tab)", "ru": "LM Studio не запущен — включи сервер в LM Studio (вкладка Developer)"},
    "Лура не запускає LM Studio сама — лише під'єднується до вже запущеного сервера (вкладка Developer у LM Studio).": {"en": "Lura never starts LM Studio itself — it only connects to a server you have already started (Developer tab in LM Studio).", "ru": "Лура не запускает LM Studio сама — только подключается к уже запущенному серверу (вкладка Developer в LM Studio)."},
    "LM Studio — усе вручну: Лура не запускає ні сервер, ні модель. Увімкни їх у LM Studio сам; llama.cpp запускається автоматично.": {"en": "LM Studio is fully manual: Lura starts neither the server nor the model. Enable them in LM Studio yourself; llama.cpp starts automatically.", "ru": "LM Studio — всё вручную: Лура не запускает ни сервер, ни модель. Включи их в LM Studio сам; llama.cpp запускается автоматически."},
    "Не обов'язково: модель зі списку LM Studio, яку має використовувати Лура. Порожньо — та, що завантажена.": {"en": "Optional: the LM Studio model Lura should use. If empty, the loaded one.", "ru": "Не обязательно: модель из списка LM Studio, которую должна использовать Лура. Если пусто — загруженная."},
    "Нагадування": {"en": "Reminders", "ru": "Напоминания"},
    "— немає —": {"en": "— none —", "ru": "— нет —"},
    "Ось файли:": {"en": "Here are the files:", "ru": "Вот файлы:"},
    "Ось скріншот екрана:": {"en": "Here is the screenshot:", "ru": "Вот снимок экрана:"},
    "Я трохи заплуталась — забагато кроків. Спробуємо ще раз?": {"en": "I got a little lost — too many steps. Shall we try again?", "ru": "Я немного запуталась — слишком много шагов. Попробуем ещё раз?"},
    "Показати / згорнути": {"en": "Show / minimize", "ru": "Показать / свернуть"},
    "Для нових анімацій встанови залежності з requirements.txt": {"en": "For the new animations install the dependencies from requirements.txt", "ru": "Для новых анимаций установи зависимости из requirements.txt"},
    "Не знайшла openlura-engine поруч із програмою": {"en": "Could not find openlura-engine next to the app", "ru": "Не нашла openlura-engine рядом с программой"},
    "вкажи llama-server у налаштуваннях": {"en": "set the llama-server path in Settings", "ru": "укажи llama-server в настройках"},
    "вкажи файл моделі .gguf для «{label}» у налаштуваннях": {"en": "set the .gguf model file for «{label}» in Settings", "ru": "укажи файл модели .gguf для «{label}» в настройках"},
    "запускаю {label}…": {"en": "starting {label}…", "ru": "запускаю {label}…"},
    "не вдалось запустити: {err}": {"en": "could not start it: {err}", "ru": "не удалось запустить: {err}"},
    "{label} зупинився: {err}": {"en": "{label} stopped: {err}", "ru": "{label} остановился: {err}"},
    "{label} готовий": {"en": "{label} is ready", "ru": "{label} готов"},
    "{label}: завантажую модель… {n} с": {"en": "{label}: loading the model… {n} s", "ru": "{label}: загружаю модель… {n} с"},
    "не знайшла файл vision-моделі — перевір шлях у налаштуваннях": {"en": "vision model file not found — check the path in Settings", "ru": "не нашла файл vision-модели — проверь путь в настройках"},
    "vision-модель": {"en": "vision model", "ru": "vision-модель"},
    "LM Studio готовий": {"en": "LM Studio is ready", "ru": "LM Studio готов"},
    "жодної": {"en": "none", "ru": "ни одной"},
    "LM Studio: модель «{name}» не завантажена — увімкни її у LM Studio. Завантажені: {ids}": {"en": "LM Studio: the model «{name}» is not loaded — enable it in LM Studio. Loaded: {ids}", "ru": "LM Studio: модель «{name}» не загружена — включи её в LM Studio. Загруженные: {ids}"},
    "Сервіс": {"en": "Service", "ru": "Сервис"},
    "API-ключ": {"en": "API key", "ru": "API-ключ"},
    "Адреса сервісу (base URL)": {"en": "Service URL (base URL)", "ru": "Адрес сервиса (base URL)"},
    "Оновити список моделей": {"en": "Refresh the model list", "ru": "Обновить список моделей"},
    "Завантажую список моделей…": {"en": "Loading the model list…", "ru": "Загружаю список моделей…"},
    "моделей у списку: {n}": {"en": "models in the list: {n}", "ru": "моделей в списке: {n}"},
    "Натисни ⟳ — підвантажу моделі з сервісу (потрібен ключ)": {"en": "Press ⟳ to load models from the service (a key is needed)", "ru": "Нажми ⟳ — подгружу модели из сервиса (нужен ключ)"},
    "Не вдалося отримати список": {"en": "Could not fetch the list", "ru": "Не удалось получить список"},
    "Введи API-ключ — тоді підвантажу список моделей.": {"en": "Enter the API key first, then I'll load the model list.", "ru": "Введи API-ключ — тогда подгружу список моделей."},
    "Введи ключ Google API — тоді підвантажу список моделей.": {"en": "Enter the Google API key first, then I'll load the model list.", "ru": "Введи ключ Google API — тогда подгружу список моделей."},
    "Користувацький (OpenAI-сумісний)": {"en": "Custom (OpenAI-compatible)", "ru": "Пользовательский (OpenAI-совместимый)"},
})
def T(text): return TRANSLATIONS.get(text, {}).get(LANG, text)

STARTUP_GREETINGS = {
    "en": ["Hi! I'm Lura 😊", "Hello! It's lovely to see you 💙", "Hey there! Ready to chat? ✨", "Welcome back! What shall we do today? 🌷", "Hi-hi! I’m here for you 😊", "Oh, you're here! Let's make something fun 💫"],
    "uk": ["Привіт! Я Лура 😊", "Вітаю, рада тебе бачити 💙", "Привіт-привіт! Поговоримо? ✨", "З поверненням! Що сьогодні робитимемо? 🌷", "Я тут! Розповідай, що нового 😊", "О, ти прийшов! Давай щось вигадаємо 💫"],
    "ru": ["Привет! Я Лура 😊", "Здравствуй, рада тебя видеть 💙", "Привет-привет! Поговорим? ✨", "С возвращением! Чем займёмся сегодня? 🌷", "Я здесь! Рассказывай, что нового 😊", "О, ты пришёл! Давай что-нибудь придумаем 💫"],
}
def startup_greeting(lang=None):
    return random.choice(STARTUP_GREETINGS.get(lang or LANG, STARTUP_GREETINGS["en"]))

def jload(p, d):
    try: return json.loads(Path(p).read_text("utf-8"))
    except Exception: return d
def jsave(p, o):
    try: Path(p).write_text(json.dumps(o, ensure_ascii=False, indent=1), "utf-8")
    except Exception: pass
def lerp(a, b, t): return a + (b - a) * t
def clamp(x, a, b): return max(a, min(b, x))
def rgba(t): return f"rgba({t[0]},{t[1]},{t[2]},{t[3] / 255:.3f})"

DEFAULT_CFG = {"provider": "cloud", "cloud_provider": "openrouter", "openrouter_key": "", "openrouter_model": "google/gemini-3-flash-preview",
               "api_keys": {}, "api_models": {}, "api_bases": {}, "api_models_cache": {},
               "google_model": "gemini-3-flash-preview", "google_api_key": "",
               "local_backend": "llamacpp", "llama_exe": "", "llama_model_path": "", "llama_vision_model": "", "llama_port": 8080, "llama_ctx": 8192,
               "llama_ngl": 99, "llama_args": "", "llama_autostart": True, "lmstudio_url": "http://127.0.0.1:1234/v1", "local_model": "local", "lmstudio_vision_model": "",
               "vision": True, "shortcuts_dir": str(HOME / "games"), "confirm_dangerous": True, "allowed_cmds": [],
               "proactive": True, "proactive_min": 25, "proactive_max": 70, "user_name": "", "theme": "dark", "sound": True,
               "font": "Nunito", "emoji_set": "apple", "language": "en", "chat_w": 370, "chat_h": 580, "orb_size": 84,
               "face_rgb": [215, 104, 152], "auto_emotion_color": True,
               "emotionality": "lively", "sarcasm": True, "hurt": True}
def load_cfg():
    c = dict(DEFAULT_CFG); c.update(jload(CFG_P, {}))
    c = {k: v for k, v in c.items() if not k.startswith("_")}   # службові ключі (типу _lms_resolved_model) не зберігаються
    for k in ("api_keys", "api_models", "api_bases", "api_models_cache", "allowed_cmds"):
        c[k] = dict(c.get(k) or [])        # вкладені словники — глибока копія, інакше шаряться з DEFAULT_CFG між викликами
    # Колір більше не налаштовується вручну: лишаємо рожеву базу та авто-відтінок емоції.
    c["auto_emotion_color"] = True
    # 430×860 були тимчасовими розмірами; повертаємо звичне вікно 370×580.
    if (c.get("chat_w"), c.get("chat_h")) == (430, 860): c["chat_w"], c["chat_h"] = 370, 580
    c["face_rgb"] = list(DEFAULT_CFG["face_rgb"])
    if c["provider"] == "llamacpp": c["provider"], c["local_backend"] = "local", "llamacpp"
    if c["provider"] in ("openrouter", "google"):
        c["cloud_provider"] = c["provider"]; c["provider"] = "cloud"
    if c.get("cloud_provider") not in CLOUD_SERVICES: c["cloud_provider"] = "openrouter"
    # старі окремі поля ключів/моделей → нові словники api_keys/api_models (сервісів тепер багато)
    keys, models = c.setdefault("api_keys", {}), c.setdefault("api_models", {})
    if c.get("openrouter_key") and not keys.get("openrouter"): keys["openrouter"] = c["openrouter_key"]
    if c.get("google_api_key") and not keys.get("google"): keys["google"] = c["google_api_key"]
    if c.get("openrouter_model") and not models.get("openrouter"): models["openrouter"] = c["openrouter_model"]
    if c.get("google_model") and not models.get("google"): models["google"] = c["google_model"]
    c.setdefault("api_bases", {}); c.setdefault("api_models_cache", {})
    # Gemini 2.5 Flash was retired on OpenRouter on 2026-10-20; migrate old configs.
    if c.get("openrouter_model") == "google/gemini-2.5-flash":
        c["openrouter_model"] = DEFAULT_CFG["openrouter_model"]; models["openrouter"] = c["openrouter_model"]
    if (models.get("google") or "").startswith(("gemini-3.8", "gemini-1.5", "gemini-2.0")):
        models["google"] = DEFAULT_CFG["google_model"]              # застарілі назви моделей Google
    c["openrouter_key"] = c.get("openrouter_key") or os.environ.get("LURA_OPENROUTER_KEY", "")
    if c["openrouter_key"] and not keys.get("openrouter"): keys["openrouter"] = c["openrouter_key"]
    return c

# ── хмарні API-сервіси: усі OpenAI-сумісні + Google + Anthropic + користувацькі
# kind: "openai" (спільний шлях /chat/completions), "google" (Gemini REST), "anthropic" (/v1/messages)
T_SYS_CUSTOM = "Користувацький (OpenAI-сумісний)"
T_SYS_CUSTOM_SHORT = "Свій (OpenAI)"
CLOUD_SERVICES = {
    "openrouter": dict(title="OpenRouter", short="OpenRouter", kind="openai", base="https://openrouter.ai/api/v1", key_ph="sk-or-…",
                       default="google/gemini-3-flash-preview",
                       extra={"HTTP-Referer": "http://localhost", "X-Title": "Lura"}),
    "google":     dict(title="Google Gemini", short="Google", kind="google", key_ph="AIza…", default="gemini-3-flash-preview"),
    "groq":       dict(title="Groq", short="Groq", kind="openai", base="https://api.groq.com/openai/v1", key_ph="gsk_…",
                       default="llama-3.3-70b-versatile"),
    "mistral":    dict(title="Mistral", short="Mistral", kind="openai", base="https://api.mistral.ai/v1", key_ph="…32 chars",
                       default="mistral-small-latest"),
    "deepseek":   dict(title="DeepSeek", short="DeepSeek", kind="openai", base="https://api.deepseek.com/v1", key_ph="sk-…",
                       default="deepseek-chat"),
    "openai":     dict(title="OpenAI (GPT)", short="OpenAI GPT", kind="openai", base="https://api.openai.com/v1", key_ph="sk-proj-…",
                       default="gpt-4o-mini"),
    "anthropic":  dict(title="Anthropic (Claude)", short="Claude", kind="anthropic", base="https://api.anthropic.com", key_ph="sk-ant-…",
                       default="claude-sonnet-4-20250514"),
    "darker":     dict(title="DarkerAPI", short="DarkerAPI", kind="openai", base="https://api.darkerapi.com/v1", key_ph="sk-…",
                       default="gpt-4o-mini", base_edit=True),
    "custom":     dict(title=T_SYS_CUSTOM, short=T_SYS_CUSTOM_SHORT, kind="openai", base="", key_ph="sk-…", default="", base_edit=True),
}
def svc_key(cfg, s): return str((cfg.get("api_keys") or {}).get(s) or "").strip()
def svc_model(cfg, s):
    m = str((cfg.get("api_models") or {}).get(s) or "").strip()
    return m or CLOUD_SERVICES.get(s, {}).get("default", "")
def svc_base(cfg, s):
    b = str((cfg.get("api_bases") or {}).get(s) or "").strip()
    return b or CLOUD_SERVICES.get(s, {}).get("base", "")

# ═══════════════════════════ ТЕМИ І ШРИФТ ═══════════════════════════
THEMES = {
 "dark": dict(bg0=(76, 43, 67), bg1=(10, 17, 21), line=(250, 246, 249), fg="#f7f1f5", fg2="#c9b3c1", bub=(255, 255, 255, 24),
              ubub="#ad4f78", ufg="#ffffff", inp=(255, 255, 255, 18), inpb=(231, 139, 177, 105), icon=(250, 239, 245),
              btn=(255, 255, 255, 22), btnh=(255, 255, 255, 52), glow=122, mfill=(150, 156, 175), hatch=(255, 122, 174),
              acc="#ee88b1", dlg="#19151d", dlgb="#5c354b", border=(223, 145, 180), white_mix=0.0, pill=(255, 255, 255, 25)),
 "light": dict(bg0=(255, 248, 251), bg1=(248, 238, 245), line=(74, 30, 50), fg="#4a2236", fg2="#a77c90", bub=(150, 60, 110, 24),
               ubub="#e8628f", ufg="#ffffff", inp=(255, 255, 255, 215), inpb=(225, 110, 155, 125), icon=(92, 42, 66),
               btn=(150, 60, 110, 24), btnh=(150, 60, 110, 52), glow=150, mfill=(255, 170, 190), hatch=(255, 110, 150),
               acc="#e8628f", dlg="#fff6fa", dlgb="#e6b3c6", border=(220, 130, 165), white_mix=0.55, pill=(255, 255, 255, 170)),
}
TH = {}
def set_theme(n): TH.clear(); TH.update(THEMES[n]); TH["name"] = n
set_theme("dark")
FONT = "Nunito"
FONT_SCALE = 1.1   # 1.0 = як зараз, 1.25 = на чверть більше, 1.5 = помітно більше
def ufont(px=14, w=500):
    f = QFont(FONT); f.setPixelSize(round(px * FONT_SCALE))
    try: f.setVariableAxis(QFont.Tag("wght"), w)
    except Exception: f.setBold(w >= 600)
    return f

APP_DIR = Path(__file__).resolve().parent
OPENLURA_DIR = APP_DIR / "openlura-engine" / "openlura-main"
def start_openlura_assets():
    if not (OPENLURA_DIR / "face-widget.html").is_file(): return None, ""
    try:
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(OPENLURA_DIR)))
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True, name="lura-face-assets").start()
        return server, f"http://127.0.0.1:{server.server_port}/face-widget.html"
    except OSError:
        return None, ""

OPENLURA_EMOTIONS = {
    "neutral":"calm", "calm":"calm", "happy":"happy", "joy":"joy", "playful":"playful",
    "sarcastic":"sarcastic", "surprised":"surprised", "sad":"sad", "worried":"worried",
    "hurt":"hurt", "irritated":"irritated", "angry":"angry", "sleepy":"sleepy", "sleeping":"sleeping",
    "thinking":"thinking", "love":"love", "bliss":"delighted", "tender":"tender", "shy":"shy",
    "excited":"excited", "confused":"confused", "proud":"proud", "scared":"scared", "bored":"bored",
    "curious":"curious", "laugh":"laugh", "cry":"crying", "crying":"crying", "wink":"wink",
    "dizzy":"dizzy", "focused":"focused", "listening":"listening", "delighted":"delighted",
    "relieved":"relieved", "skeptical":"skeptical", "mischievous":"mischievous", "anticipates":"anticipates",
    "inquisitive":"inquisitive", "daydream":"daydream", "cozy":"cozy", "giggle":"giggle", "pout":"pout",
    "determined":"determined", "shocked":"shocked", "dreamy":"dreamy", "oops":"oops", "tired":"tired", "party":"party"
}
FONT_DIRS = [APP_DIR, APP_DIR / "fonts", FONT_DIR]      # шрифти шукаємо поруч зі скриптом (і в ./fonts), потім у ~/.lura/fonts
def load_fonts():
    """Зареєструвати (встановити для програми) шрифти .ttf/.otf, що лежать поруч зі скриптом. Нічого не скачує.
    Повертає (усі родини, родини з папки скрипта)."""
    families, local, seen = [], [], set()
    for d in FONT_DIRS:
        if not d.is_dir(): continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in (".ttf", ".otf") or f.resolve() in seen: continue
            seen.add(f.resolve()); font_id = QFontDatabase.addApplicationFont(str(f))
            if font_id < 0: continue
            fam = QFontDatabase.applicationFontFamilies(font_id); families.extend(fam)
            if d in (APP_DIR, APP_DIR / "fonts"): local.extend(fam)
    return families, local

# ═══════════════════════════ МОРДАШКА: емоції ═══════════════════════════
BASE = dict(open=1.0, w=1.0, tilt=0.0, lash=1.0, lash_ang=0.0, mouth=0.2, mw=0.8, mo=0.0, my=0.0, mfill=0.0,
            blush=0.0, tear=0.0, sweat=0.0, sy=0.0, gap=1.0, shake=0.0, lo=1.0, ro=1.0, lx=0.0, ly=0.0,
            hearts=0.0, r=70, g=120, b=255)
def E(style="oval", ms="line", extra="", wink=0, c=None, **kw):
    d = dict(kw)
    if c: d["r"], d["g"], d["b"] = c
    d.update(_style=style, _ms=ms, _extra=extra, _wink=wink)
    return d
PRESETS = {   # зроблено за скріншотами оригінальної Лури
 "neutral": E(),
 "happy": E(mouth=.85, mw=.95, blush=.15, c=(90, 160, 255)),
 "joy": E("arc", mouth=1, mw=2.0, mo=.5, mfill=.35, blush=.2, c=(255, 205, 90)),
 "bliss": E("arc", "cat", blush=1, hearts=.45, c=(255, 85, 150)),
 "love": E("heart", "cat", blush=.9, hearts=1, c=(255, 90, 160)),
 "laugh": E("arc", mouth=1, mw=2.2, mo=1, mfill=.35, shake=.8, tear=.3, blush=.4, c=(255, 200, 90)),
 "excited": E(open=1.12, w=1.12, mouth=1, mw=1.2, mo=.5, mfill=.35, lash=1.3, lash_ang=12, c=(255, 170, 80)),
 "sparkle": E("star", "dot", blush=.2, c=(170, 120, 255)),
 "sad": E(tilt=-13, open=.85, lash_ang=-28, mouth=-.7, mw=.7, my=.04, ly=.3, c=(60, 90, 210)),
 "cry": E(tilt=-15, open=.8, lash_ang=-30, mouth=-.9, mw=1, mo=.45, mfill=.3, tear=1, shake=.35, c=(60, 100, 230)),
 "angry": E(tilt=16, open=.7, mouth=-.7, mw=.9, lash_ang=10, c=(255, 70, 60)),
 "annoyed": E(tilt=8, open=.55, mouth=-.25, mw=.7, lash_ang=-6, c=(255, 140, 80)),
 "surprised": E(open=1.3, w=.82, mouth=0, mw=.6, lash=1.2, lash_ang=18, c=(140, 200, 255)),
 "shocked": E(open=1.4, w=.8, mo=.9, mfill=.35, mw=.7, mouth=0, shake=.5, sweat=.6, lash_ang=22, c=(170, 190, 255)),
 "scared": E(tilt=-10, open=1.2, w=.9, mouth=-.3, mo=.35, mfill=.35, mw=1, shake=1, sweat=1, c=(120, 130, 255)),
 "thinking": E(extra="q", open=.9, sy=-.1, tilt=4, mouth=0, mw=.55, my=.02, lx=.6, ly=-.6, c=(120, 150, 255)),
 "confused": E(extra="q", lo=.85, ro=1.2, tilt=-5, mouth=-.15, mw=.7, lx=-.3, c=(150, 130, 255)),
 "cringe": E("chevron", "blob", sweat=1, c=(70, 90, 220)),
 "embarrassed": E("chevron", "line", blush=1, sweat=.5, mouth=-.2, mw=.7, mo=.45, mfill=1, c=(255, 125, 165)),
 "shy": E("oval", "dot", open=.92, w=1.1, blush=1, lx=-.6, ly=.5, c=(255, 135, 175)),
 "wink": E("oval", "blob", wink=1, c=(155, 95, 255)),
 "smug": E(open=.6, tilt=5, mouth=.65, mw=.9, lash_ang=-8, c=(150, 100, 255)),
 "proud": E(open=.85, tilt=3, mouth=.75, mw=.9, lash=1.25, ly=-.4, blush=.2, c=(255, 200, 90)),
 "curious": E(open=1.1, lo=1.05, ro=.9, lash_ang=12, mouth=.1, mw=.6, lx=.35, c=(100, 210, 255)),
 "worried": E(tilt=-12, mouth=-.4, mw=.8, sweat=.4, lash_ang=-15, c=(110, 130, 230)),
 "bored": E(open=.5, w=1.15, mouth=-.1, mw=.6, ly=.25, lash_ang=-10, c=(110, 120, 160)),
 "silly": E(lo=.75, ro=1.25, mouth=.6, mo=.8, mfill=.35, mw=1.3, tilt=-4, c=(255, 170, 230)),
 "dizzy": E("spiral", mouth=-.1, mw=.7, mo=.2, mfill=.3, shake=.3, c=(170, 140, 255)),
 "determined": E(tilt=13, open=.85, mouth=.3, mw=.9, lash_ang=8, c=(255, 150, 60)),
 "mischievous": E(tilt=10, open=.75, mouth=.95, mw=1.2, blush=.2, c=(185, 90, 255)),
 "sick": E(open=.6, tilt=-8, mouth=-.4, mw=.7, sweat=.5, c=(120, 200, 130)),
 "tender": E(open=.75, mouth=.6, mw=.8, blush=.35, c=(120, 205, 235)),
 "sleepy": E(open=.3, lash_ang=-22, mouth=0, mo=.2, mfill=.3, mw=.5, ly=.4, c=(80, 100, 200)),
 "sleeping": E("line", extra="z", mouth=0, mo=.15, mw=.5, lash_ang=-25, c=(70, 90, 190)),
}
ALIASES = {"smile": "happy", "mad": "angry", "heart": "love", "think": "thinking", "sleep": "sleeping", "tired": "sleepy",
           "sorry": "sad", "blush": "shy", "surprise": "surprised", "afraid": "scared", "fear": "scared", "cool": "smug",
           "calm": "tender", "wow": "surprised", "lol": "laugh", "cute": "bliss", "glad": "happy", "upset": "sad",
           "nervous": "worried", "hug": "tender", "ouch": "cringe", "awkward": "cringe", "stars": "sparkle", "yay": "joy",
           "cozy": "tender", "giggle": "laugh", "playful": "mischievous", "inquisitive": "curious",
           "reconciled": "tender", "hurt": "sad", "pout": "annoyed"}
EMO = {"😊": "happy", "😄": "joy", "😂": "laugh", "🥰": "bliss", "😍": "love", "❤": "love", "😢": "sad", "😭": "cry",
       "😡": "angry", "😮": "surprised", "😱": "scared", "🤔": "thinking", "😴": "sleepy", "😉": "wink", "😏": "smug",
       "😳": "embarrassed", "🥺": "sad", "✨": "sparkle", "😅": "cringe", "😎": "smug"}

def local_emotion(text):
    """Невелика офлайн-реакція мордашки, коли мовну модель не під'єднано."""
    for icon, emotion in EMO.items():
        if icon in text: return emotion
    s = text.casefold()
    groups = (
        ("sad", ("сумно", "сумую", "погано", "сумний", "грустно", "грущу", "sad", "cry", "плачу")),
        ("angry", ("злюсь", "бісить", "ненавиджу", "роздратований", "злюсь", "angry", "hate")),
        ("scared", ("страшно", "боюся", "боюсь", "лякає", "страшно", "afraid", "scared")),
        ("love", ("кохаю", "люблю", "обіймаю", "love you", "hug")),
        ("happy", ("чудово", "супер", "класно", "дякую", "радий", "рада", "щаслив", "great", "thanks", "happy")),
    )
    for emotion, words in groups:
        if any(word in s for word in words): return emotion
    if "?" in s or any(word in s for word in ("чому", "як це", "що таке", "why", "how")): return "curious"
    return "neutral"

def resolve(n):
    n = n.strip().lower()
    if n in PRESETS: return n
    if n in ALIASES: return ALIASES[n]
    m = difflib.get_close_matches(n, list(PRESETS), 1, .7)
    return m[0] if m else None

# ── як у мобільній Лурі: репліки під час погладжування та розпізнавання настрою користувача
PET_LINES = {
    "uk": ["ой, дякую", "ой… дякую", "мурр", "ще погладь, будь ласка", "ще трошки, будь ласка", "мені приємно", "ти такий теплий", "ой, лоскотно"],
    "en": ["oh, thank you", "mrr", "pet me more, please", "just a bit more, please", "that feels nice", "you're so warm", "oh, that tickles"],
    "ru": ["ой спасибки", "ой… спасибо", "мурр", "ещё погладь, пожалуйста", "ещё чуть-чуть, пожалуйста", "мне приятно", "ты такой тёплый", "ой, щекотно"],
}
NEW_CHAT_GREETING = {"uk": "Привіт. Я Лура. Як ти?", "en": "Hi. I'm Lura. How are you?", "ru": "Привет. Я Лура. Как ты?"}

def detect_user_emotion(text):
    """Емоція користувача з його ж повідомлення (як у мобільній версії): грубість → злість/образа тощо."""
    s = text.casefold()
    to_her = re.search(r"\b(ти|тебе|тво[яїй]|тобі|тобой)\b", s)
    if re.search(r"бля|ху[йяеї]|пізд|єб|ёб|еб[аиу]|сук[аи]|мудак|долбо|шлюх", s):
        return "angry" if to_her else "irritated"
    if re.search(r"ненави|вбий|заткни|ідіот|идиот|дура|туп|бісить|бесит|достав|мерза|тварюка|тварь", s):
        return "hurt" if re.search(r"ненави|вбий", s) else "angry"
    if re.search(r"сумн|груст|погано|плохо|втоми|втомив|устал|важко|тяжело|самотн|одинок|плач|депрес", s): return "sad"
    if re.search(r"люблю|кохаю|дякую|спасибо|мила|умниц|розумниц|клас|класс|супер|обожню|обожаю", s): return "shy"
    if re.search(r"жарт|шут|сміш|смеш|лол|хаха|ахах", s): return "playful"
    if text.strip().endswith("?"): return "curious"
    return None

def pet_line():
    """Репліка під час погладжування — мовою з налаштувань (як і весь бесідовий текст Лури)."""
    return random.choice(PET_LINES.get(LANG, PET_LINES["uk"]))

def parse_spec(s):
    weights, custom = {}, {}
    for tok in re.split(r"[,\s;]+", s.strip()):
        if not tok: continue
        if "=" in tok:
            k, v = tok.split("=", 1)
            try: custom[k.strip().lower()] = float(v)
            except ValueError: pass
        else:
            n, _, w = tok.partition(":"); n = resolve(n)
            if n:
                try: weights[n] = float(w) if w else 1.0
                except ValueError: weights[n] = 1.0
    return weights, custom

class Face:
    def __init__(self):
        # Базовий вираз — усмішка (як у 😊); нейтральний лишається для стану «думаю/друкую».
        base = {k: PRESETS["happy"].get(k, BASE[k]) for k in BASE}
        self.cur, self.tgt = dict(base), dict(base)
        self.style, self.ms, self.extra = "oval", "line", ""
        self.gx = self.gy = 0.0; self.pop = 0.0; self.pop_tgt = 0.0; self.bounce = 0.0; self.talk = 0.0; self.talking = False
        self.bl = {-1: -1.0, 1: -1.0}; self.next_blink = time.time() + 2; self.hold_until = 0.0; self.base_spec = "happy"; self.typing = False

    def set(self, spec, hold=9.0):
        w, custom = parse_spec(spec)
        if not w and not custom: return
        w = {k: v for k, v in w.items() if v > 0}
        tot = sum(w.values())
        if tot < 1: w["neutral"] = w.get("neutral", 0) + (1 - tot); tot = 1
        w = {k: v / tot for k, v in w.items()}
        tgt = {k: 0.0 for k in BASE}
        for n, wt in w.items():
            for k in BASE: tgt[k] += wt * PRESETS[n].get(k, BASE[k])
        # «генерація»: кожна емоція щоразу трохи різниться розміром і виразом, без нахилу мордашки
        for k in ("open", "w", "lash", "mw"): tgt[k] *= random.uniform(.96, 1.04)
        tgt["lo"] *= random.uniform(.94, 1.06); tgt["ro"] *= random.uniform(.94, 1.06)
        tgt["tilt"] += random.uniform(-1.5, 1.5); tgt["lash_ang"] += random.uniform(-2, 2); tgt["mouth"] += random.uniform(-.05, .05)
        ww = sum(w[n] for n in w if PRESETS[n]["_wink"])
        if ww >= .3:
            k = random.choice(("lo", "ro")); tgt[k] = lerp(tgt[k], .26, min(1, ww * 1.2))
        for k, v in custom.items():
            if k in BASE: tgt[k] = v
        top = max((n for n in w if PRESETS[n]["_style"] != "oval"), key=lambda n: w[n], default=None)
        self.style = PRESETS[top]["_style"] if top and w[top] >= .4 else "oval"
        tm = max((n for n in w if PRESETS[n]["_ms"] != "line"), key=lambda n: w[n], default=None)
        self.ms = PRESETS[tm]["_ms"] if tm and w[tm] >= .4 else "line"
        self.extra = next((PRESETS[n]["_extra"] for n in w if PRESETS[n]["_extra"] and w[n] >= .35), "")
        self.tgt = tgt; self.pop_tgt = 1.0      # «подскок» наростає плавно — мордашка не підскакує ривком
        self.hold_until = time.time() + hold if hold > 0 else 0

    def blink(self, sd):
        p = self.bl[sd]; return 1 - .96 * math.sin(math.pi * p) if p >= 0 else 1.0
    def blink_eye(self, sd): self.bl[sd] = 0.0      # кліпнути лише одним оком

    def step(self, now, dt_, cg):
        k = 1 - math.exp(-dt_ * 10)
        for key in self.cur: self.cur[key] += (self.tgt[key] - self.cur[key]) * k
        self.pop += (self.pop_tgt - self.pop) * (1 - math.exp(-dt_ * 26)); self.pop_tgt *= math.exp(-dt_ * 5)
        self.bounce *= math.exp(-dt_ * 3.5)
        self.talk += ((1.0 if self.talking else 0.0) - self.talk) * (1 - math.exp(-dt_ * 12))
        if self.hold_until and now > self.hold_until: self.set(self.base_spec, hold=0)
        for sd in (-1, 1):
            if self.bl[sd] >= 0:
                self.bl[sd] += dt_ / .17
                if self.bl[sd] >= 1: self.bl[sd] = -1.0
        if not self.typing and self.bl[-1] < 0 and self.bl[1] < 0 and now > self.next_blink and self.style != "line":
            self.bl[-1] = self.bl[1] = 0.0; self.next_blink = now + (.18 if random.random() < .15 else random.uniform(2.2, 5.5))
        lx, ly = self.cur["lx"], self.cur["ly"]
        bw = clamp(math.hypot(lx, ly) * 1.4, 0, 1)
        tx, ty = cg[0] * (1 - bw) + lx * bw, cg[1] * (1 - bw) + ly * bw
        kk = 1 - math.exp(-dt_ * 12)
        self.gx += (tx - self.gx) * kk; self.gy += (ty - self.gy) * kk

def heart_path(h):
    path = QPainterPath(); path.moveTo(0, h * .9)
    path.cubicTo(-h * 1.6, -h * .1, -h * .7, -h * 1.2, 0, -h * .35)
    path.cubicTo(h * .7, -h * 1.2, h * 1.6, -h * .1, 0, h * .9); return path

def draw_eye(p, sd, ex, ey, st, f, now, pen, lpen, line):
    style = f.style
    op = st["open"] * (st["lo"] if sd < 0 else st["ro"]); pop = 1 + f.pop * .1
    rx = 21 * st["w"] * pop
    ry = max(2.2, 29 * clamp(op, .05, 1.6) * pop * (f.blink(sd) if style == "oval" else 1))
    p.save(); p.translate(ex, ey)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
    rxl, ryl = rx, ry
    if style == "oval": p.drawEllipse(QPointF(0, 0), rx, ry)          # без зіниць — як в оригіналі
    elif style == "arc":
        rxa, ha = rx * 1.7, rx * 1.2; path = QPainterPath(); rect = QRectF(-rxa, -ha + 7, 2 * rxa, 2 * ha)
        path.arcMoveTo(rect, 0); path.arcTo(rect, 0, 180); p.drawPath(path); rxl, ryl = rxa * .9, ha * .85
    elif style == "line":
        rxa, ha = rx * 1.2, rx * .5; path = QPainterPath(); rect = QRectF(-rxa, -ha, 2 * rxa, 2 * ha)
        path.arcMoveTo(rect, 195); path.arcTo(rect, 195, 150); p.drawPath(path); rxl, ryl = rxa, 8
    elif style == "chevron":
        h = ry * .62; w_ = rx * 1.05; path = QPainterPath()
        path.moveTo(sd * w_, -h); path.lineTo(-sd * w_, 0); path.lineTo(sd * w_, h); p.drawPath(path); rxl, ryl = w_, h * .9
    elif style == "heart":
        h = rx * 1.45 * (1 + .1 * math.sin(now * 8)); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 105, 150))
        p.drawPath(heart_path(h)); rxl, ryl = rx * 1.3, 14
    elif style == "star":
        R = rx * 1.9 * (1 + .05 * math.sin(now * 3)); path = QPainterPath()
        for i in range(8):
            a = math.pi * i / 4 - math.pi / 2; rad = R if i % 2 == 0 else R * .28
            (path.moveTo if i == 0 else path.lineTo)(rad * math.cos(a), rad * math.sin(a))
        path.closeSubpath(); p.drawPath(path); rxl, ryl = R * .8, R * .55
    else:  # spiral
        path = QPainterPath()
        for i in range(70):
            a = i * .33 + now * 6 * -sd; r = rx * 1.4 * i / 70
            (path.moveTo if i == 0 else path.lineTo)(r * math.cos(a), r * math.sin(a))
        p.drawPath(path); rxl, ryl = rx * 1.3, 14
    p.setPen(lpen)   # вії: три паралельні штрихи віялом, з відступом від ока (як в оригіналі)
    for idx, (u, d, L) in enumerate(((50, 46, .92), (26, 22, 1.12), (3, 2, .95))):
        ur, dr = math.radians(u), math.radians(d)
        sx = sd * (rxl * math.cos(ur) + 5.5 * math.cos(dr)); sy = -(ryl * math.sin(ur) + 5.5 * math.sin(dr))
        ln = rx * 1.15 * L * st["lash"]; ex_, ey_ = sx + sd * ln * math.cos(dr), sy - ln * math.sin(dr)
        p.drawLine(QPointF(sx, sy), QPointF(ex_, ey_))
        if idx == 0 and sd > 0:   # фірмова краплинка на кінці верхньої війки
            vx, vy = sd * math.cos(dr), -math.sin(dr)
            p.save(); p.translate(ex_ + vx * 5, ey_ + vy * 5); p.rotate(math.degrees(math.atan2(vy, vx)))
            p.setPen(QPen(line, 2.2)); p.drawEllipse(QPointF(0, 0), 4.6, 2.7); p.restore()
    p.restore()

def draw_face(p, c, s, f, now):
    st = f.cur; line = QColor(*TH["line"])
    p.save(); p.translate(c); p.scale(s * (1 + .06 * f.bounce * math.sin(now * 18)), s * (1 - .05 * f.bounce * math.sin(now * 18)))
    p.translate(f.gx * 8, f.gy * 5 + st["sy"] * 20 + math.sin(now * 1.6) * 1.1)
    gap, shk = 46 * st["gap"], st["shake"]
    if st["blush"] > .03:   # рум'янець: м'яка пляма + штрихи «////»
        b = clamp(st["blush"], 0, 1); hc = QColor(*TH["hatch"])
        for sd in (-1, 1):
            cx, cy = sd * gap * .98, 28
            p.save(); p.translate(cx, cy); p.scale(1, .46)
            g = QRadialGradient(QPointF(0, 0), 25); c1 = QColor(hc); c1.setAlpha(int(120 * b)); c0 = QColor(hc); c0.setAlpha(0)
            g.setColorAt(0, c1); g.setColorAt(1, c0); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g)); p.drawEllipse(QPointF(0, 0), 25, 25); p.restore()
            hc2 = QColor(hc); hc2.setAlpha(int(255 * clamp(b * 1.3, 0, 1))); hp = QPen(hc2, 2.2); hp.setCapStyle(Qt.PenCapStyle.RoundCap); p.setPen(hp)
            for i in range(4): x = cx - 9 + i * 6; p.drawLine(QPointF(x, cy + 4), QPointF(x + 4, cy - 4))
    pen = QPen(line, 5.6); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    lpen = QPen(line, 4.8); lpen.setCapStyle(Qt.PenCapStyle.RoundCap)
    for sd in (-1, 1):
        draw_eye(p, sd, sd * gap + shk * 1.8 * math.sin(now * 47 + sd), -6 + shk * 1.5 * math.sin(now * 53 + sd * 2), st, f, now, pen, lpen, line)
    if st["tear"] > .05:
        p.setPen(Qt.PenStyle.NoPen)
        for sd in (-1, 1):
            ph = (now * .9 + (.4 if sd > 0 else 0)) % 1
            p.setBrush(QColor(120, 190, 255, int((1 - ph) * clamp(st["tear"], 0, 1) * 230))); p.drawEllipse(QPointF(sd * (gap - 4), 24 + ph * 34), 3.2, 4.8)
    if st["sweat"] > .05:
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(150, 200, 255, int(clamp(st["sweat"], 0, 1) * 220)))
        p.drawEllipse(QPointF(gap + 34, -34 + math.sin(now * 3) * 2), 3, 4.8)
    p.save(); p.translate(f.gx * 3, f.gy * 2)   # рот
    my, mw, cv = 32 + st["my"] * 30, 9 * st["mw"] * (1 + f.talk * .15), st["mouth"]
    ms = "line" if f.talk > .3 else f.ms
    mo = clamp(st["mo"] + f.talk * (.28 + .25 * math.sin(now * 17) + .1 * math.sin(now * 29)), 0, 1.2)
    if ms == "dot":
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(line); p.drawEllipse(QPointF(0, my), 4.8, 4.8)
    elif ms == "blob":
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(line)
        for dx, dy, r in ((-4.5, 1, 3.6), (0, -.6, 4.4), (4.5, 1, 3.6)): p.drawEllipse(QPointF(dx, my + dy), r, r * .85)
    elif ms == "cat":
        path = QPainterPath(); path.moveTo(-mw * .95, my - 1); path.quadTo(-mw * .5, my + 9, 0, my - 1); path.quadTo(mw * .5, my + 9, mw * .95, my - 1)
        p.setPen(QPen(line, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
    else:
        path = QPainterPath(); path.moveTo(-mw, my)
        if mo > .12:
            path.quadTo(0, my + cv * 6, mw, my); path.quadTo(0, my + 3 + cv * 3 + mo * 26, -mw, my); path.closeSubpath()
            mf = st["mfill"]; mc = TH["mfill"]; fc_ = QColor(int(lerp(mc[0], line.red(), mf)), int(lerp(mc[1], line.green(), mf)), int(lerp(mc[2], line.blue(), mf)), int(lerp(190, 255, mf)))
            p.setPen(QPen(line, 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)); p.setBrush(fc_)
        else:
            path.quadTo(0, my + cv * 10, mw, my); p.setPen(QPen(line, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    p.restore()
    p.setPen(QColor(line.red(), line.green(), line.blue(), 190)); p.setBrush(Qt.BrushStyle.NoBrush)
    if f.extra == "z":
        for i in range(3):
            ph = (now * .5 + i / 3) % 1; fnt = ufont(10, 700); fnt.setPixelSize(int(11 + 9 * ph))
            p.setFont(fnt); p.setOpacity(math.sin(math.pi * ph)); p.drawText(QPointF(gap + 26 + ph * 16, -26 - ph * 30), "z")
        p.setOpacity(1)
    elif f.extra == "q":
        p.setFont(ufont(24, 700)); p.drawText(QPointF(gap + 28, -38 + math.sin(now * 3) * 3), "?")
    p.restore()

# ═══════════════════════════ ІНСТРУМЕНТИ МАЛЮВАННЯ: іконки, перемикачі ═══════════════════════════
def draw_icon(p, name, rc, col):
    p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = min(rc.width(), rc.height()); p.translate(rc.center())
    pen = QPen(col, s * .11, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin); p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
    def fill(): p.setPen(Qt.PenStyle.NoPen); p.setBrush(col)
    if name == "gear":
        R, r, hole = s * .5, s * .37, s * .17; path = QPainterPath(); first = True
        for k in range(8):
            a0 = k * math.pi / 4
            for da, rad in ((-.21, r), (-.14, R), (.14, R), (.21, r)):
                pt = QPointF(rad * math.cos(a0 + da), rad * math.sin(a0 + da))
                if first: path.moveTo(pt); first = False
                else: path.lineTo(pt)
        path.closeSubpath(); path.addEllipse(QPointF(0, 0), hole, hole); path.setFillRule(Qt.FillRule.OddEvenFill); fill(); p.drawPath(path)
    elif name == "eye":   # миле «око Лури»: овал, вії, іскорка
        pen.setWidthF(s * .1); p.setPen(pen); p.drawEllipse(QPointF(s * .05, s * .03), s * .21, s * .29)
        for a, ln in ((-62, .2), (-38, .22), (-14, .19)):
            ar = math.radians(a); x0, y0 = -s * .27 * math.cos(ar) - s * .04, s * .03 + s * .02 + s * .3 * math.sin(ar)
            p.drawLine(QPointF(x0, y0), QPointF(x0 - s * ln * math.cos(ar), y0 + s * ln * math.sin(ar)))
        fill(); st_ = QPainterPath(); cx, cy, R, r = s * .05, s * .02, s * .13, s * .035
        for i in range(8):
            a = math.pi * i / 4 - math.pi / 2; rad = R if i % 2 == 0 else r
            (st_.moveTo if i == 0 else st_.lineTo)(cx + rad * math.cos(a), cy + rad * math.sin(a))
        st_.closeSubpath(); p.drawPath(st_)
    elif name == "clip":      # скріпка
        p.rotate(40); p.scale(.82, .82); path = QPainterPath()
        path.moveTo(s * .12, -s * .14); path.lineTo(s * .12, s * .20); path.arcTo(QRectF(-s * .12, s * .08, s * .24, s * .24), 0, -180)
        path.lineTo(-s * .12, -s * .26); path.arcTo(QRectF(-s * .12, -s * .44, s * .36, s * .36), 180, -180)
        path.lineTo(s * .24, s * .26); path.arcTo(QRectF(-s * .24, s * .02, s * .48, s * .48), 0, -180); path.lineTo(-s * .24, -s * .10); p.drawPath(path)
    elif name == "file":      # аркуш із загнутим кутом
        path = QPainterPath(); path.moveTo(-s * .30, -s * .44); path.lineTo(s * .08, -s * .44); path.lineTo(s * .30, -s * .22)
        path.lineTo(s * .30, s * .44); path.lineTo(-s * .30, s * .44); path.closeSubpath(); p.drawPath(path)
        p.drawLine(QPointF(s * .08, -s * .44), QPointF(s * .08, -s * .22)); p.drawLine(QPointF(s * .08, -s * .22), QPointF(s * .30, -s * .22))
    elif name == "back": p.drawLine(QPointF(s * .12, -s * .3), QPointF(-s * .18, 0)); p.drawLine(QPointF(-s * .18, 0), QPointF(s * .12, s * .3))
    elif name == "send":
        path = QPainterPath(); path.moveTo(-s * .46, -s * .38); path.lineTo(s * .5, 0); path.lineTo(-s * .46, s * .38); path.lineTo(-s * .24, 0); path.closeSubpath(); fill(); p.drawPath(path)
    elif name == "close": p.drawLine(QPointF(-s * .27, -s * .27), QPointF(s * .27, s * .27)); p.drawLine(QPointF(-s * .27, s * .27), QPointF(s * .27, -s * .27))
    elif name == "min": p.drawLine(QPointF(-s * .3, s * .08), QPointF(s * .3, s * .08))
    elif name == "more":
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(col)
        for x in (-s*.28, 0, s*.28): p.drawEllipse(QPointF(x,0),s*.075,s*.075)
    elif name == "menu":      # три риски
        for k in (-.22, 0, .22): p.drawLine(QPointF(-s * .3, k * s), QPointF(s * .3, k * s))
    elif name == "sun":
        p.drawEllipse(QPointF(0, 0), s * .2, s * .2)
        for k in range(8):
            a = k * math.pi / 4; p.drawLine(QPointF(math.cos(a) * s * .32, math.sin(a) * s * .32), QPointF(math.cos(a) * s * .47, math.sin(a) * s * .47))
    elif name == "moon":
        a = QPainterPath(); a.addEllipse(QPointF(0, 0), s * .4, s * .4); b = QPainterPath(); b.addEllipse(QPointF(s * .2, -s * .12), s * .35, s * .35)
        fill(); p.drawPath(a.subtracted(b))
    p.restore()

class IconButton(QPushButton):
    def __init__(self, icon, parent=None, checkable=False):
        super().__init__(parent); self.icon_name = icon; self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFlat(True); self.accent = False
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        on = self.isChecked() or self.accent
        bg = QColor(TH["acc"]) if on else QColor(*(TH["btnh"] if self.underMouse() else TH["btn"]))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(bg); p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        col = QColor("#ffffff") if on else QColor(*TH["icon"]); ih = r.height() * (.6 if self.icon_name == "eye" else .52)
        draw_icon(p, self.icon_name, QRectF(r.center().x() - ih / 2, r.center().y() - ih / 2, ih, ih), col)

class Switch(QWidget):
    toggled = pyqtSignal(bool)
    def __init__(self, on=False):
        super().__init__(); self.on = on; self.k = 1.0 if on else 0.0; self.setFixedSize(46, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.t = QTimer(self); self.t.timeout.connect(self._step)
    def set_on(self, v): self.on = bool(v); self.t.start(16)
    def mousePressEvent(self, e): self.on = not self.on; self.t.start(16); self.toggled.emit(self.on)
    def _step(self):
        tg = 1.0 if self.on else 0.0; self.k += (tg - self.k) * .35
        if abs(tg - self.k) < .01: self.k = tg; self.t.stop()
        self.update()
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        off, on = QColor(*TH["btnh"]), QColor(TH["acc"])
        c = QColor(int(lerp(off.red(), on.red(), self.k)), int(lerp(off.green(), on.green(), self.k)), int(lerp(off.blue(), on.blue(), self.k)), int(lerp(off.alpha(), 255, self.k)))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c); p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setBrush(QColor("#ffffff")); p.drawEllipse(QPointF(lerp(r.left() + 12, r.right() - 12, self.k), r.center().y()), 9, 9)

class Segmented(QWidget):
    """Ковзний перемикач-сегмент (замість хмаринки/комп'ютера)."""
    changed = pyqtSignal(int)
    def __init__(self, items, idx=0, h=30):
        super().__init__(); self.items, self.idx, self.k = items, idx, float(idx); self.setFixedHeight(h)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.t = QTimer(self); self.t.timeout.connect(self._step)
    def set_index(self, i, emit=False):
        if i == self.idx: return
        self.idx = i; self.t.start(16)
        if emit: self.changed.emit(i)
    def _step(self):
        self.k += (self.idx - self.k) * .3
        if abs(self.idx - self.k) < .01: self.k = float(self.idx); self.t.stop()
        self.update()
    def mousePressEvent(self, e):
        i = int(clamp(e.position().x() // (self.width() / len(self.items)), 0, len(self.items) - 1))
        if i != self.idx: self.set_index(i, True)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(*TH["btn"])); p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        sw = r.width() / len(self.items); hl = QRectF(r.x() + self.k * sw + 2.5, r.y() + 2.5, sw - 5, r.height() - 5)
        p.setBrush(QColor(TH["acc"])); p.drawRoundedRect(hl, hl.height() / 2, hl.height() / 2); p.setFont(ufont(10 if len(self.items) > 2 else 12, 700))
        for i, t in enumerate(self.items):
            sel = 1 - clamp(abs(self.k - i), 0, 1); c = QColor(*TH["icon"]); w = QColor("#ffffff")
            p.setPen(QColor(int(lerp(c.red(), 255, sel)), int(lerp(c.green(), 255, sel)), int(lerp(c.blue(), 255, sel)), int(lerp(170, 255, sel))))
            p.drawText(QRectF(r.x() + i * sw, r.y(), sw, r.height()), Qt.AlignmentFlag.AlignCenter, t)

# ═══════════════════════════ ЕМОДЗІ як у Telegram (картинки) ═══════════════════════════
EM_RE = re.compile("(?:[\U0001F1E6-\U0001F1FF]{2}|[#*0-9]\uFE0F?\u20E3|[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B05-\u2B07\u2B1B\u2B1C\u2B50\u2B55"
                   "\u2934\u2935\u2194-\u2199\u21A9\u21AA\u231A\u231B\u2328\u23CF\u23E9-\u23F3\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB-\u25FE"
                   "\u2139\u203C\u2049\u3030\u303D\u3297\u3299][\uFE0F\U0001F3FB-\U0001F3FF]?"
                   "(?:\u200D[\U0001F300-\U0001FAFF\u2600-\u27BF\u2640\u2642\u2764][\uFE0F\U0001F3FB-\U0001F3FF]?)*)")
ONLY_EMO = re.compile("^(?:" + EM_RE.pattern + r"\s*){1,3}$")
EMOJI_SETS = {   # apple — як у Telegram Desktop; кеш у ~/.lura/emoji/<набір>/
 "apple": ["https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-64/{code}.png",
           "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.1.2/img/apple/64/{code}.png"],
 "twemoji": ["https://raw.githubusercontent.com/jdecked/twemoji/main/assets/72x72/{code}.png",
             "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/{code}.png"]}
EMOJI_SET = "apple"; EMO_FAIL, EMO_PEND = set(), set()
class EmoSig(QObject): ready = pyqtSignal()
EMO_SIG = None
def emoji_key(seq): return "-".join(c for c in (f"{ord(ch):x}" for ch in seq) if c != "fe0f")
def emoji_path(key): return EMO_DIR / EMOJI_SET / f"{key}.png"
def fetch_emoji(seq):
    key = emoji_key(seq)
    try:
        raw = "-".join(f"{ord(ch):x}" for ch in seq)
        cands = list(dict.fromkeys([key, raw, key + "-fe0f"]))
        if EMOJI_SET == "twemoji": cands = [raw if "200d" in raw else key]
        (EMO_DIR / EMOJI_SET).mkdir(parents=True, exist_ok=True); ok = False
        for url in EMOJI_SETS[EMOJI_SET]:
            for cd in cands:
                try:
                    r = requests.get(url.format(code=cd), timeout=8, headers=UA)
                    if r.status_code == 200 and r.content[:4] == b"\x89PNG": emoji_path(key).write_bytes(r.content); ok = True; break
                except Exception: break
            if ok: break
        if not ok: EMO_FAIL.add(key)
    finally:
        EMO_PEND.discard(key)
        if EMO_SIG is not None: EMO_SIG.ready.emit()
def to_html(text, size=20):
    miss = False; t = htmlmod.escape(text)
    t = re.sub(r"```(.*?)```", lambda m: "<pre>" + m[1].strip("\r\n") + "</pre>", t, flags=re.S)
    t = re.sub(r"`([^`\r\n]+)`", r"<code>\1</code>", t)
    t = re.sub(r"(?m)^#{1,3}\s*(.+)$", r"<b>\1</b>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)([^*\r\n]+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", t)
    t = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" style="color:#7ea2ff">\1</a>', t)
    t = re.sub(r"(?m)^\s*[-•]\s+", "• ", t).replace("\r\n", "<br>")
    def rep(m):
        nonlocal miss
        key = emoji_key(m[0]); path = emoji_path(key)
        if path.exists(): return f'<img src="{path.as_uri()}" width="{size}" height="{size}" style="vertical-align:middle">'
        if key not in EMO_FAIL:
            miss = True
            if key not in EMO_PEND: EMO_PEND.add(key); threading.Thread(target=fetch_emoji, args=(m[0],), daemon=True).start()
        return m[0]
    return EM_RE.sub(rep, t), miss
def prefetch_emoji(text):
    for m in set(EM_RE.findall(text)):
        if not emoji_path(emoji_key(m)).exists() and emoji_key(m) not in EMO_FAIL: EMO_PEND.add(emoji_key(m)); fetch_emoji(m)

def make_ping(path):
    sr = 44100; total = int(sr * .8); buf = [0.0] * total
    for fr, t0, amp in ((1046.5, 0, .5), (1568.0, .11, .45)):
        for i in range(int(sr * .6)):
            t = i / sr; env = math.exp(-t * 7) * min(1, t * 200); j = i + int(t0 * sr)
            if j < total: buf[j] += amp * env * (math.sin(2 * math.pi * fr * t) + .25 * math.sin(4 * math.pi * fr * t))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(clamp(x, -1, 1) * 30000)) for x in buf))

# ═══════════════════════════ ІНСТРУМЕНТИ (tool calling) ═══════════════════════════
def fn(name, desc, props=None, req=()):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props or {}, "required": list(req)}}}
S = lambda d: {"type": "string", "description": d}
N = lambda d: {"type": "number", "description": d}
B = lambda d: {"type": "boolean", "description": d}
TOOLS = [
 fn("open_app", "Відкрити програму/гру/файл/папку. Відомі (chrome, notepad, calc, explorer, discord, steam...) запускаються одразу; решта — шукається в папці ярликів.", {"name": S("назва програми, гри або шлях")}, ["name"]),
 fn("list_shortcuts", "Показати список ярликів (ігри/програми) з папки ярликів."),
 fn("open_urls", "Відкрити один або кілька сайтів у браузері. Для пошуку: https://www.google.com/search?q=...", {"urls": {"type": "array", "items": {"type": "string"}, "description": "список URL"}}, ["urls"]),
 fn("search_web", "Знайти інформацію в інтернеті (повертає заголовки, посилання, уривки).", {"query": S("запит")}, ["query"]),
 fn("fetch_page", "Завантажити сторінку за URL і повернути її текст (для читання/переказу).", {"url": S("URL"), "max_chars": N("ліміт символів, типово 8000")}, ["url"]),
 fn("run_terminal", "Виконати команду в терміналі (cmd або powershell) і повернути вивід. Команди зі списку дозволених користувачем виконуються без питань.", {"command": S("команда"), "shell": S("cmd або powershell"), "timeout": N("секунд, до 120"), "cwd": S("робоча папка")}, ["command"]),
 fn("read_file", "Прочитати файл (txt, md, код, json, csv, pdf, docx).", {"path": S("шлях"), "max_chars": N("ліміт, типово 15000")}, ["path"]),
 fn("write_file", "Записати/дописати текстовий файл.", {"path": S("шлях"), "content": S("текст"), "append": B("дописати замість заміни")}, ["path", "content"]),
 fn("list_dir", "Показати вміст папки.", {"path": S("шлях, типово домашня папка")}),
 fn("find_files", "Знайти файли за маскою імені (наприклад *.pdf або *звіт*).", {"pattern": S("маска"), "root": S("де шукати")}, ["pattern"]),
 fn("clipboard_get", "Прочитати текст з буфера обміну."),
 fn("clipboard_set", "Записати текст у буфер обміну.", {"text": S("текст")}, ["text"]),
 fn("look_at_screen", "Зробити скріншот екрана і подивитись на нього."),
 fn("wait", "Почекати кілька секунд (напр. поки програма запуститься).", {"seconds": N("1-10")}, ["seconds"]),
 fn("active_window", "Заголовок активного вікна."),
 fn("system_info", "Час, ОС, CPU/RAM/батарея і (опційно) запущені програми.", {"processes": B("показати топ процесів")}),
 fn("close_top_window", "Закрити верхнє вікно на екрані (те, що зараз поверх усіх; власне вікно Лури не враховується). Використовуй, коли просять «закрий програму/вікно» без уточнення."),
 fn("close_app", "Закрити програму за назвою процесу (напр. chrome).", {"process_name": S("ім'я процесу")}, ["process_name"]),
 fn("mouse_click", "Клік мишею по координатах зі скріншота (після look_at_screen).", {"x": N("x"), "y": N("y"), "button": S("left/right"), "double": B("подвійний")}, ["x", "y"]),
 fn("type_text", "Надрукувати текст у активному полі (будь-якою мовою).", {"text": S("текст")}, ["text"]),
 fn("press_keys", "Натиснути клавішу/комбінацію, напр. enter, ctrl+c, alt+tab, win+d.", {"keys": S("комбінація через +")}, ["keys"]),
 fn("scroll", "Прокрутити (додатне — вгору, від'ємне — вниз).", {"amount": N("кількість")}, ["amount"]),
 fn("remember", "Запам'ятати важливий ФАКТ про користувача (ім'я, вподобання, проєкти, люди...).", {"key": S("коротка назва"), "value": S("факт")}, ["key", "value"]),
 fn("forget", "Забути факт.", {"key": S("назва")}, ["key"]),
 fn("recall", "Показати все, що запам'ятала (факти й побажання щодо спілкування)."),
 fn("save_preference", "Зберегти побажання користувача щодо МАНЕРИ СПІЛКУВАННЯ/поведінки (напр. «відповідай коротко», «звертайся на ти», «жартуй менше», «не пиши першою»). Викликай одразу, коли користувач про це просить.", {"text": S("побажання одним реченням")}, ["text"]),
 fn("remove_preference", "Видалити збережене побажання за id.", {"id": N("id")}, ["id"]),
 fn("set_behavior", "Змінити поведінку програми: чи писати першою, як часто (хвилини), чи грати звук повідомлень. Нагадування від цього НЕ залежать.", {"proactive": B("писати першою"), "proactive_min": N("мін. інтервал, хв"), "proactive_max": N("макс. інтервал, хв"), "sound": B("звук повідомлень")}),
 fn("set_reminder", "Поставити нагадування (через N хвилин або на конкретний час).", {"text": S("про що"), "in_minutes": N("через скільки хвилин"), "at": S("'YYYY-MM-DD HH:MM' або 'HH:MM'"), "repeat_minutes": N("повторювати кожні N хв (необов'язково)")}, ["text"]),
 fn("list_reminders", "Список нагадувань."),
 fn("cancel_reminder", "Скасувати нагадування.", {"id": N("id")}, ["id"]),
]
TOOL_LABELS = {
    "uk": {"open_app": "відкриваю програму", "open_urls": "відкриваю сайти", "search_web": "шукаю в інтернеті", "fetch_page": "читаю сторінку",
           "run_terminal": "працюю з терміналом", "look_at_screen": "дивлюсь на екран", "read_file": "читаю файл", "write_file": "пишу файл",
           "remember": "запам'ятовую", "save_preference": "запам'ятовую побажання", "set_reminder": "ставлю нагадування",
           "close_top_window": "закриваю вікно", "mouse_click": "клікаю", "type_text": "друкую", "press_keys": "натискаю клавіші"},
    "ru": {"open_app": "открываю программу", "open_urls": "открываю сайты", "search_web": "ищу в интернете", "fetch_page": "читаю страницу",
           "run_terminal": "работаю с терминалом", "look_at_screen": "смотрю на экран", "read_file": "читаю файл", "write_file": "пишу файл",
           "remember": "запоминаю", "save_preference": "запоминаю пожелание", "set_reminder": "ставлю напоминание",
           "close_top_window": "закрываю окно", "mouse_click": "кликаю", "type_text": "печатаю", "press_keys": "нажимаю клавиши"},
    "en": {"open_app": "opening the app", "open_urls": "opening sites", "search_web": "searching the web", "fetch_page": "reading the page",
           "run_terminal": "working in the terminal", "look_at_screen": "looking at the screen", "read_file": "reading the file", "write_file": "writing the file",
           "remember": "memorizing", "save_preference": "saving the preference", "set_reminder": "setting a reminder",
           "close_top_window": "closing the window", "mouse_click": "clicking", "type_text": "typing", "press_keys": "pressing keys"},
}
def tool_label(name): return TOOL_LABELS.get(LANG, TOOL_LABELS["uk"]).get(name, name)
# якщо модель після дій нічого не написала — Лура каже коротко сама; мова — як у користувача
FEEDBACK_LINES = {
    "uk": {"*": ["Готово 😉", "Зробила!", "Ось так ✨"],
           "open_urls": ["Відкрила 😉", "Тримай, відкрила", "Дивись, відкрила"],
           "open_app": ["Запустила! 🚀", "Ось, запустила", "Відкриваю 😉"],
           "search_web": ["Ось що знайшла 🔍", "Знайла!", "Пошукала — тримай"],
           "run_terminal": ["Зробила в терміналі", "Готово, ось результат"],
           "look_at_screen": ["Бачу екран 👀", "Дивлюсь..."],
           "read_file": ["Прочитала 📖", "Ось, що там"],
           "write_file": ["Зберегла 📝", "Записала!"],
           "set_reminder": ["Нагадаю ⏰", "Нагадування на місці!"],
           "remember": ["Запам'ятала 💗", "Записала собі"],
           "fetch_page": ["Ось, прочитала", "Прочитала сторінку 📖"]},
    "ru": {"*": ["Готово 😉", "Сделала!", "Вот так ✨"],
           "open_urls": ["Открыла 😉", "Держи, открыла", "Смотри, открыла"],
           "open_app": ["Запустила! 🚀", "Вот, запустила", "Открываю 😉"],
           "search_web": ["Вот что нашла 🔍", "Нашла!", "Поискала — держи"],
           "run_terminal": ["Сделала в терминале", "Готово, вот результат"],
           "look_at_screen": ["Вижу экран 👀", "Смотрю..."],
           "read_file": ["Прочитала 📖", "Вот, что там"],
           "write_file": ["Сохранила 📝", "Записала!"],
           "set_reminder": ["Напомню ⏰", "Напоминание на месте!"],
           "remember": ["Запомнила 💗", "Записала себе"],
           "fetch_page": ["Вот, прочитала", "Прочитала страницу 📖"]},
    "en": {"*": ["Done 😉", "Did it!", "Like so ✨"],
           "open_urls": ["Opened 😉", "There you go", "See, opened"],
           "open_app": ["Launched! 🚀", "There, launched", "Opening 😉"],
           "search_web": ["Here's what I found 🔍", "Found it!", "Searched — here"],
           "run_terminal": ["Done in the terminal", "Here's the result"],
           "look_at_screen": ["I see the screen 👀", "Looking..."],
           "read_file": ["Read it 📖", "Here's what's inside"],
           "write_file": ["Saved 📝", "Wrote it down!"],
           "set_reminder": ["I'll remind you ⏰", "Reminder set!"],
           "remember": ["Remembered 💗", "Noted"],
           "fetch_page": ["Here, read it", "Read the page 📖"]},
}

KNOWN = {"chrome": "chrome", "google chrome": "chrome", "хром": "chrome", "firefox": "firefox", "edge": "msedge", "браузер": "chrome",
         "notepad": "notepad", "блокнот": "notepad", "calculator": "calc", "calc": "calc", "калькулятор": "calc",
         "explorer": "explorer", "провідник": "explorer", "проводник": "explorer", "cmd": "cmd", "powershell": "powershell",
         "terminal": "wt", "термінал": "wt", "paint": "mspaint", "settings": "ms-settings:", "налаштування": "ms-settings:",
         "task manager": "taskmgr", "диспетчер завдань": "taskmgr", "vscode": "code", "vs code": "code", "word": "winword",
         "excel": "excel", "powerpoint": "powerpnt", "spotify": "spotify", "discord": "discord", "telegram": "telegram",
         "steam": "steam", "obs": "obs64", "snipping tool": "snippingtool"}
SC_EXT = {".lnk", ".url", ".exe", ".bat", ".cmd", ".desktop", ".sh"}
BAD_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Windows.UI.Core.CoreWindow", "NotifyIconOverflowWindow"}

def launch(t):
    if IS_WIN: os.startfile(t); return
    if IS_MAC:
        r = subprocess.run(["open", t] if os.path.exists(t) else ["open", "-a", t], capture_output=True)
        if r.returncode: raise FileNotFoundError(t)
        return
    alt = {"chrome": ["google-chrome", "chromium", "chrome"], "calc": ["gnome-calculator", "kcalc"], "notepad": ["gedit", "kate", "mousepad"], "explorer": ["xdg-open"]}
    for c in alt.get(t, [t]):
        w = shutil.which(c) or (c if os.path.exists(c) else None)
        if w:
            if w.endswith(".desktop") or not os.access(w, os.X_OK): subprocess.Popen(["xdg-open", w])
            else: subprocess.Popen([w], start_new_session=True)
            return
    raise FileNotFoundError(t)

def list_sc(d):
    base, out = Path(d), []
    if not base.exists(): return out
    for root, dirs, files in os.walk(base):
        if len(Path(root).relative_to(base).parts) > 2: dirs[:] = []; continue
        out += [Path(root) / f for f in files if Path(f).suffix.lower() in SC_EXT]
    return out
def norm(s): return re.sub(r"[^\w]+", " ", s.lower()).strip()
def find_sc(d, q):
    q, best = norm(q), (0, None)
    for pth in list_sc(d):
        n = norm(pth.stem)
        sc = 1.0 if n == q else .9 if q and (q in n or n in q) else difflib.SequenceMatcher(None, q, n).ratio()
        if sc > best[0]: best = (sc, pth)
    return best[1] if best[0] >= .55 else None

def decode(b):
    enc = "cp866"
    if IS_WIN:
        try:
            import ctypes; enc = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception: pass
    for e in ("utf-8", enc):
        try: return b.decode(e)
        except Exception: pass
    return b.decode("utf-8", "replace")

def html_to_text(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg|head).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h\d>", "\r\n", h)
    h = htmlmod.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"[ \t]+", " ", re.sub(r"\r\n\s*\r\n+", "\r\n\r\n", h)).strip()

def top_window_excluding(skip):
    """Windows: перше видиме вікно в Z-порядку, крім наших власних."""
    import ctypes
    from ctypes import wintypes
    u, dwm, found = ctypes.windll.user32, ctypes.windll.dwmapi, []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _l):
        if not h or int(h) in skip or not u.IsWindowVisible(h) or u.IsIconic(h): return True
        n = u.GetWindowTextLengthW(h)
        if n == 0 or (u.GetWindowLongW(h, -20) & 0x80): return True
        cls = ctypes.create_unicode_buffer(256); u.GetClassNameW(h, cls, 256)
        if cls.value in BAD_CLASSES: return True
        cl = wintypes.DWORD(0); dwm.DwmGetWindowAttribute(h, 14, ctypes.byref(cl), 4)
        if cl.value: return True
        buf = ctypes.create_unicode_buffer(n + 1); u.GetWindowTextW(h, buf, n + 1); found.append((int(h), buf.value)); return False
    u.EnumWindows(cb, 0)
    return found[0] if found else None

def ask_dialog(text):
    m = QMessageBox(); m.setWindowTitle("Лура питає"); m.setText(text); m.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    a = m.addButton("Дозволити", QMessageBox.ButtonRole.AcceptRole)
    al = m.addButton("Завжди (до перезапуску)", QMessageBox.ButtonRole.AcceptRole)
    m.addButton("Ні", QMessageBox.ButtonRole.RejectRole); m.exec(); b = m.clickedButton()
    return "always" if b is al else "yes" if b is a else "no"

class Bridge(QObject):
    """Виконує функції в GUI-потоці на прохання потоку-агента."""
    req = pyqtSignal(object)
    def __init__(self): super().__init__(); self.req.connect(self._run)
    def _run(self, job):
        try: job["res"] = job["fn"]()
        except Exception as ex: job["res"] = f"ERROR: {ex}"
        job["ev"].set()
    def call(self, f, timeout=120):
        job = {"fn": f, "ev": threading.Event(), "res": None}
        self.req.emit(job); job["ev"].wait(timeout); return job["res"]

class Tools:
    def __init__(self, app): self.app = app; self.trusted = set(); self.images = []; self.last_shot = None
    def run(self, name, args):
        f = getattr(self, "t_" + name, None)
        if not f: return f"Невідомий інструмент {name}"
        try: return str(f(**args))
        except TypeError as ex: return f"Неправильні аргументи: {ex}"
        except Exception as ex: return f"Помилка: {ex}"
    def confirm(self, kind, text):
        if not self.app.cfg["confirm_dangerous"] or kind in self.trusted: return True
        r = self.app.bridge.call(lambda: ask_dialog(text), 300)
        if r == "always": self.trusted.add(kind)
        return r in ("yes", "always")
    def cmd_allowed(self, cmd):
        c = cmd.strip().lower()
        if re.search(r"[;&|<>`\r\n]|\$\(", c): return False       # ланцюжки команд завжди питають
        for pat in self.app.cfg.get("allowed_cmds", []):
            p = pat.strip().lower()
            if not p: continue
            if ("*" in p or "?" in p) and fnmatch.fnmatch(c, p): return True
            if c == p or c.startswith(p + " "): return True
        return False

    def t_open_app(self, name):
        key, err = name.strip().lower(), ""
        if key in KNOWN:
            try: launch(KNOWN[key]); return f"Запустила {name}"
            except Exception as ex: err = str(ex)
        p = Path(os.path.expandvars(os.path.expanduser(name)))
        if p.exists(): launch(str(p)); return f"Відкрила {p}"
        hit = find_sc(self.app.cfg["shortcuts_dir"], name)
        if hit: launch(str(hit)); return f"Запустила ярлик «{hit.stem}»"
        try: launch(name); return f"Запустила {name}"
        except Exception: pass
        names = [x.stem for x in list_sc(self.app.cfg["shortcuts_dir"])][:40]
        return f"Не знайшла «{name}». {err} Ярлики: {', '.join(names) or '(папка порожня)'}"
    def t_list_shortcuts(self):
        n = sorted({x.stem for x in list_sc(self.app.cfg["shortcuts_dir"])})
        return f"Папка: {self.app.cfg['shortcuts_dir']}\r\n" + (", ".join(n[:300]) or "порожньо")
    def t_open_urls(self, urls):
        for u in urls: webbrowser.open_new_tab(u if re.match(r"^\w+://", u) else "https://" + u); time.sleep(.35)
        return f"Відкрила {len(urls)} вкладок"
    def t_search_web(self, query, num=6):
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=UA, timeout=20)
        items = re.findall(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', r.text, re.S)
        out = []; cl = lambda x: htmlmod.unescape(re.sub(r"<.*?>", "", x)).strip()
        for href, title, snip in items[:int(num)]:
            href = htmlmod.unescape(href); q = parse_qs(urlparse(href).query)
            out.append(f"- {cl(title)}\r\n  {q['uddg'][0] if 'uddg' in q else href}\r\n  {cl(snip)}")
        return "\r\n".join(out) or "Нічого не знайшла."
    def t_fetch_page(self, url, max_chars=8000):
        r = requests.get(url, headers=UA, timeout=25); r.encoding = r.apparent_encoding or r.encoding
        return html_to_text(r.text)[:int(max_chars)]
    def t_run_terminal(self, command, shell="cmd", timeout=30, cwd=None):
        if not self.cmd_allowed(command) and not self.confirm("terminal", f"Виконати в терміналі:\r\n\r\n{command}"): return "Користувач відмовив."
        args = ["powershell", "-NoProfile", "-Command", command] if (IS_WIN and shell == "powershell") else command
        try:
            r = subprocess.run(args, shell=isinstance(args, str), capture_output=True, timeout=min(int(timeout), 120),
                               cwd=cwd or str(Path.home()), creationflags=0x08000000 if IS_WIN else 0)
        except subprocess.TimeoutExpired: return "Таймаут."
        return f"exit={r.returncode}\r\n" + (decode(r.stdout) + decode(r.stderr))[-6000:]
    def t_read_file(self, path, max_chars=15000):
        p = Path(os.path.expandvars(os.path.expanduser(path))); ext = p.suffix.lower()
        if ext == ".pdf":
            from pypdf import PdfReader
            txt = "\r\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
        elif ext == ".docx":
            import docx; txt = "\r\n".join(x.text for x in docx.Document(str(p)).paragraphs)
        else: txt = p.read_text("utf-8", errors="replace")
        return txt[:int(max_chars)]
    def t_write_file(self, path, content, append=False):
        p = Path(os.path.expandvars(os.path.expanduser(path)))
        if not self.confirm("write", f"Записати файл:\r\n{p}\r\n({len(content)} символів)"): return "Користувач відмовив."
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a" if append else "w", encoding="utf-8") as fh: fh.write(content)
        return f"Збережено {p}"
    def t_list_dir(self, path=None):
        p = Path(os.path.expandvars(os.path.expanduser(path or "~")))
        return "\r\n".join(f"{'[D] ' if x.is_dir() else ''}{x.name}" for x in sorted(p.iterdir())[:200])
    def t_find_files(self, pattern, root=None):
        root, t0, out = os.path.expanduser(root or "~"), time.time(), []
        for r, ds, fs in os.walk(root):
            ds[:] = [d for d in ds if not d.startswith(".") and d.lower() not in ("node_modules", "windows", "appdata")]
            out += [os.path.join(r, f) for f in fs if fnmatch.fnmatch(f.lower(), pattern.lower())]
            if len(out) >= 30 or time.time() - t0 > 8: break
        return "\r\n".join(out) or "Не знайшла."
    def t_clipboard_get(self): return self.app.bridge.call(lambda: QGuiApplication.clipboard().text()) or "(порожньо)"
    def t_clipboard_set(self, text): self.app.bridge.call(lambda: QGuiApplication.clipboard().setText(text)); return "Скопійовано."
    def t_look_at_screen(self):
        if not self.app.cfg["vision"]: return "Бачення екрана вимкнене в налаштуваннях."
        r = self.app.bridge.call(self.app.grab_screen)
        if not isinstance(r, tuple): return f"Не вдалось: {r}"
        self.images.append(r[0]); self.last_shot = r[1]
        return f"Скріншот {r[1][0]}x{r[1][1]} зроблено — дивись зображення нижче. Координати для кліків бери з нього."
    def t_wait(self, seconds): time.sleep(clamp(float(seconds), .5, 10)); return "ok"
    def t_active_window(self):
        if not IS_WIN: return "Підтримується лише на Windows."
        import ctypes
        u = ctypes.windll.user32; h = u.GetForegroundWindow(); b = ctypes.create_unicode_buffer(300); u.GetWindowTextW(h, b, 300)
        return b.value or "(без заголовка)"
    def t_system_info(self, processes=False):
        s = f"{dt.datetime.now():%A %Y-%m-%d %H:%M}; {platform.platform()}"
        try:
            import psutil
            s += f"; CPU {psutil.cpu_percent(.3)}%; RAM {psutil.virtual_memory().percent}%"
            b = psutil.sensors_battery()
            if b: s += f"; батарея {b.percent:.0f}%{' (заряджається)' if b.power_plugged else ''}"
            if processes:
                ps = sorted(psutil.process_iter(["name", "memory_percent"]), key=lambda x: x.info["memory_percent"] or 0, reverse=True)[:15]
                s += "\r\nПроцеси: " + ", ".join(x.info["name"] for x in ps)
        except ImportError: s += " (psutil не встановлено)"
        return s
    def t_close_top_window(self):
        if IS_WIN:
            skip = self.app.bridge.call(self.app.own_hwnds)
            hit = top_window_excluding(skip if isinstance(skip, set) else set())
            if not hit: return "Не знайшла вікна для закриття."
            if not self.confirm("close", f"Закрити вікно: {hit[1]}?"): return "Користувач відмовив."
            import ctypes; ctypes.windll.user32.PostMessageW(hit[0], 0x0010, 0, 0)    # WM_CLOSE — ввічливо
            return f"Закрила вікно «{hit[1]}»."
        xd = shutil.which("xdotool")
        if xd and self.confirm("close", "Закрити активне вікно?"): subprocess.run([xd, "getactivewindow", "windowclose"]); return "Закрила активне вікно."
        return "Закриття верхнього вікна підтримується на Windows (на Linux потрібен xdotool)."
    def t_close_app(self, process_name):
        if not self.confirm("close", f"Закрити програму: {process_name}?"): return "Користувач відмовив."
        n = process_name if process_name.lower().endswith(".exe") or not IS_WIN else process_name + ".exe"
        r = subprocess.run(["taskkill", "/IM", n, "/F"] if IS_WIN else ["pkill", "-f", process_name], capture_output=True)
        return "Закрила." if r.returncode == 0 else "Не вдалось (може, її не запущено)."
    def _gui(self):
        try: import pyautogui; pyautogui.FAILSAFE = False; return pyautogui
        except ImportError: raise RuntimeError("Потрібно: pip install pyautogui")
    def t_mouse_click(self, x, y, button="left", double=False):
        pg = self._gui()
        if not self.confirm("input", f"Клікнути мишею ({int(x)}, {int(y)})?"): return "Користувач відмовив."
        sw, sh = pg.size()
        if self.last_shot: x, y = x * sw / self.last_shot[0], y * sh / self.last_shot[1]
        pg.click(x, y, clicks=2 if double else 1, button=button); return "Клікнула."
    def t_type_text(self, text):
        pg = self._gui()
        if not self.confirm("input", f"Надрукувати текст:\r\n{text[:200]}"): return "Користувач відмовив."
        self.app.bridge.call(lambda: QGuiApplication.clipboard().setText(text)); time.sleep(.1)
        pg.hotkey("command" if IS_MAC else "ctrl", "v"); return "Надрукувала."
    def t_press_keys(self, keys):
        pg = self._gui()
        if not self.confirm("input", f"Натиснути: {keys}"): return "Користувач відмовив."
        pg.hotkey(*[k.strip() for k in keys.split("+")]); return "Натиснула."
    def t_scroll(self, amount):
        pg = self._gui()
        if not self.confirm("input", "Прокрутити сторінку?"): return "Користувач відмовив."
        pg.scroll(int(amount)); return "ok"
    def t_remember(self, key, value):
        self.app.mem["facts"][key] = value; jsave(MEM_P, self.app.mem); return f"Запам'ятала: {key} = {value}"
    def t_forget(self, key):
        self.app.mem["facts"].pop(key, None); jsave(MEM_P, self.app.mem); return "Забула."
    def t_save_preference(self, text):
        pr = self.app.mem["prefs"]
        if not any(x["text"].lower() == text.lower() for x in pr): pr.append({"id": max([x["id"] for x in pr] + [0]) + 1, "text": text})
        jsave(MEM_P, self.app.mem); return f"Запам'ятала побажання: {text}"
    def t_remove_preference(self, id):
        self.app.mem["prefs"][:] = [x for x in self.app.mem["prefs"] if x["id"] != int(id)]; jsave(MEM_P, self.app.mem); return "Прибрала."
    def t_set_behavior(self, proactive=None, proactive_min=None, proactive_max=None, sound=None):
        c = self.app.cfg
        if proactive is not None: c["proactive"] = bool(proactive)
        if proactive_min: c["proactive_min"] = max(1, int(proactive_min))
        if proactive_max: c["proactive_max"] = max(c["proactive_min"] + 1, int(proactive_max))
        if sound is not None: c["sound"] = bool(sound)
        jsave(CFG_P, c); self.app.next_pro = time.time() + random.uniform(c["proactive_min"], c["proactive_max"]) * 60
        return f"Готово: писати першою={'так' if c['proactive'] else 'ні'} ({c['proactive_min']}–{c['proactive_max']} хв), звук={'так' if c['sound'] else 'ні'}. Нагадування працюють завжди."
    def t_recall(self):
        a = "\r\n".join(f"{k}: {v}" for k, v in self.app.mem["facts"].items()) or "фактів поки нема"
        b = "\r\n".join(f"#{x['id']} {x['text']}" for x in self.app.mem["prefs"]) or "побажань поки нема"
        return f"Факти:\r\n{a}\r\nПобажання:\r\n{b}"
    def t_set_reminder(self, text, in_minutes=None, at=None, repeat_minutes=0):
        now = dt.datetime.now()
        if in_minutes is not None: due = now + dt.timedelta(minutes=float(in_minutes))
        elif at:
            s = at.strip().replace("T", " ")
            try: due = dt.datetime.fromisoformat(s)
            except ValueError:
                m = re.match(r"^(\d{1,2})[:.](\d{2})$", s)
                if not m: return "Невідомий формат часу: 'YYYY-MM-DD HH:MM' або 'HH:MM'"
                due = now.replace(hour=int(m[1]), minute=int(m[2]), second=0, microsecond=0)
                if due <= now: due += dt.timedelta(days=1)
        else: return "Вкажи in_minutes або at."
        with self.app.lock:
            rid = max([r["id"] for r in self.app.rem] + [0]) + 1
            self.app.rem.append({"id": rid, "text": text, "due": due.timestamp(), "repeat": float(repeat_minutes or 0)}); jsave(REM_P, self.app.rem)
        return f"Нагадування #{rid} на {due:%Y-%m-%d %H:%M}"
    def t_list_reminders(self):
        return "\r\n".join(f"#{r['id']} {dt.datetime.fromtimestamp(r['due']):%Y-%m-%d %H:%M} — {r['text']}" for r in self.app.rem) or "Немає."
    def t_cancel_reminder(self, id):
        with self.app.lock: self.app.rem[:] = [r for r in self.app.rem if r["id"] != int(id)]; jsave(REM_P, self.app.rem)
        return "Скасовано."

# ═══════════════════════════ LLM: стрімінг + промти ═══════════════════════════
_GOOGLE_KEY_LOCK = threading.Lock()
_GOOGLE_KEY_INDEX = 0

def load_google_keys(cfg):
    """Ключ Google — лише з поля налаштувань (і змінної оточення, якщо задана). Жодних файлів."""
    keys = [str(cfg.get("google_api_key") or svc_key(cfg, "google") or "").strip()]
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key and env_key.strip(): keys.insert(0, env_key.strip())
    keys = list(dict.fromkeys(k for k in keys if k))
    if not keys: raise RuntimeError(T("Введи ключ Google API у налаштуваннях (шестерня) — і все запрацює."))
    return keys

def next_google_key(keys):
    global _GOOGLE_KEY_INDEX
    with _GOOGLE_KEY_LOCK:
        idx = _GOOGLE_KEY_INDEX % len(keys)
        _GOOGLE_KEY_INDEX = (idx + 1) % len(keys)
    return keys[idx]

def google_schema(schema):
    """Convert the OpenAI-style function schema to Gemini REST schema."""
    if isinstance(schema, list): return [google_schema(x) for x in schema]
    if not isinstance(schema, dict): return schema
    out = {}
    properties = schema.get("properties")
    for key, value in schema.items():
        if key == "type": out[key] = str(value).upper()
        elif key == "properties":
            # словник «ім'я → схема властивості»: конвертуємо КОЖНУ властивість окремо
            out[key] = {name: google_schema(sub) for name, sub in value.items()} if isinstance(value, dict) else {}
        elif key == "items": out[key] = google_schema(value)
        elif key == "required":
            # Gemini rejects required names absent from the sibling properties map.
            valid = set(properties) if isinstance(properties, dict) else set()
            names = [name for name in value if name in valid] if isinstance(value, (list, tuple)) else []
            if names: out[key] = names
        elif key in ("description", "enum", "format", "nullable"): out[key] = value
    return out

def google_request_data(messages, tools):
    system = ""
    contents = []
    tool_names = {}
    for msg in messages:
        role = msg.get("role", "user")
        if role == "system":
            system += ("\n" if system else "") + str(msg.get("content", ""))
            continue
        parts = []
        content = msg.get("content", "")
        if isinstance(content, str):
            if content: parts.append({"text": content})
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, dict): continue
                if item.get("type") == "text": parts.append({"text": str(item.get("text", ""))})
                elif item.get("type") == "image_url":
                    uri = (item.get("image_url") or {}).get("url", "")
                    m = re.match(r"data:([^;,]+);base64,(.+)", uri, re.S)
                    if m: parts.append({"inline_data": {"mime_type": m.group(1), "data": m.group(2)}})
        if role == "assistant":
            for call in msg.get("tool_calls") or []:
                fn = call.get("function") or {}; name = fn.get("name", "")
                try: args = json.loads(fn.get("arguments") or "{}")
                except Exception: args = {}
                if name:
                    parts.append({"functionCall": {"name": name, "args": args}})
                    tool_names[call.get("id", "")] = name
            gemini_role = "model"
        elif role == "tool":
            name = tool_names.get(msg.get("tool_call_id", ""), "tool")
            parts = [{"functionResponse": {"name": name, "response": {"result": str(content)}}}]
            gemini_role = "user"
        else: gemini_role = "user"
        if parts:
            if contents and contents[-1]["role"] == gemini_role: contents[-1]["parts"].extend(parts)
            else: contents.append({"role": gemini_role, "parts": parts})
    body = {"contents": contents, "generationConfig": {"temperature": .8}}
    if system: body["systemInstruction"] = {"parts": [{"text": system}]}
    declarations = []
    for item in tools or []:
        fn = item.get("function") or {}
        if not fn.get("name"): continue
        decl = {"name": fn["name"]}
        if fn.get("description"): decl["description"] = fn["description"]
        if fn.get("parameters"): decl["parameters"] = google_schema(fn["parameters"])
        declarations.append(decl)
    if declarations: body["tools"] = [{"functionDeclarations": declarations}]
    return body

def google_generate(cfg, messages, tools=None, on_delta=None, stream=True):
    keys = load_google_keys(cfg)
    model = svc_model(cfg, "google").removeprefix("models/")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:" + ("streamGenerateContent?alt=sse" if stream else "generateContent")
    body = google_request_data(messages, tools)
    response = None; last_error = ""
    for _ in range(len(keys)):
        key = next_google_key(keys)
        try:
            r = requests.post(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                             json=body, timeout=(15, 240), stream=stream)
        except requests.RequestException as ex:
            last_error = str(ex); continue
        if r.status_code == 200:
            response = r; break
        try: detail = r.json().get("error", {}).get("message", r.text[:300])
        except Exception: detail = r.text[:300]
        last_error = f"{r.status_code}: {detail}"; status = r.status_code; r.close()
        if status not in (401, 403, 429): raise RuntimeError(last_error)
    if response is None: raise RuntimeError("Google Gemini: запит відхилено всіма ключами. " + last_error)
    content, calls = "", {}
    try:
        if stream:
            events = (line.decode("utf-8", "ignore")[5:].strip() for line in response.iter_lines() if line and line.startswith(b"data:"))
            chunks = (json.loads(data) for data in events if data and data != "[DONE]")
        else: chunks = iter([response.json()])
        for chunk in chunks:
            if chunk.get("error"): raise RuntimeError(str(chunk["error"])[:300])
            for candidate in chunk.get("candidates") or []:
                parts = ((candidate.get("content") or {}).get("parts") or [])
                for part_index, part in enumerate(parts):
                    if part.get("text"):
                        content += part["text"]
                        if on_delta: on_delta(content)
                    fc = part.get("functionCall") or {}
                    if fc.get("name"):
                        calls[part_index] = {"id": f"google-{part_index}", "type": "function",
                            "function": {"name": fc["name"], "arguments": json.dumps(fc.get("args") or {}, ensure_ascii=False)}}
    finally: response.close()
    return {"content": content, "tool_calls": [calls[i] for i in sorted(calls)]}

def api_provider(cfg):
    """Return the selected cloud API backend, or the local backend."""
    return cfg.get("cloud_provider", "openrouter") if cfg.get("provider") == "cloud" else cfg.get("provider", "cloud")

def anthropic_request_data(messages, tools):
    """Конвертація OpenAI-стилю в Messages API Anthropic (roles чергуються, tool_use/tool_result блоками)."""
    system, out = "", []
    for msg in messages:
        role, content = msg.get("role"), msg.get("content", "")
        if role == "system":
            system += ("\n" if system else "") + str(content); continue
        if role == "tool":      # результат інструмента — блоком у role "user"
            out.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": msg.get("tool_call_id", ""),
                                                     "content": str(content)}]})
        elif role == "assistant":
            blocks = []
            if isinstance(content, str) and content: blocks.append({"type": "text", "text": content})
            for call in msg.get("tool_calls") or []:
                fn = call.get("function") or {}
                try: args = json.loads(fn.get("arguments") or "{}")
                except Exception: args = {}
                if fn.get("name"):
                    blocks.append({"type": "tool_use", "id": call.get("id") or fn["name"], "name": fn["name"], "input": args})
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
        else:                   # user
            if isinstance(content, str):
                out.append({"role": "user", "content": [{"type": "text", "text": content or " "}]})
            else:
                blocks = []
                for item in content if isinstance(content, list) else []:
                    if not isinstance(item, dict): continue
                    if item.get("type") == "text": blocks.append({"type": "text", "text": str(item.get("text", ""))})
                    elif item.get("type") == "image_url":
                        m = re.match(r"data:([^;,]+);base64,(.+)", (item.get("image_url") or {}).get("url", ""), re.S)
                        if m: blocks.append({"type": "image", "source": {"type": "base64", "media_type": m.group(1), "data": m.group(2)}})
                out.append({"role": "user", "content": blocks or [{"type": "text", "text": " "}]})
    merged = []      # Anthropic вимагає чергування ролей — зливаємо сусідні однакові
    for m in out:
        if merged and merged[-1]["role"] == m["role"]: merged[-1]["content"] = merged[-1]["content"] + m["content"]
        else: merged.append(m)
    body = {"max_tokens": 2048, "temperature": .8, "messages": merged}
    if system: body["system"] = system
    if tools:
        body["tools"] = [{"name": (f.get("function") or {}).get("name"),
                          "description": (f.get("function") or {}).get("description", ""),
                          "input_schema": (f.get("function") or {}).get("parameters") or {"type": "object", "properties": {}}}
                         for f in tools if (f.get("function") or {}).get("name")]
    return body

def anthropic_generate(cfg, messages, tools=None, on_delta=None, stream=True):
    """Anthropic Messages API: стрімінг SSE (text_delta / input_json_delta) і tool_use блоки."""
    svc = api_provider(cfg); key = svc_key(cfg, svc)
    if not key: raise RuntimeError(f"Немає ключа {CLOUD_SERVICES[svc]['title']} — відкрий налаштування (шестерня) і встав його.")
    body = anthropic_request_data(messages, tools); body["model"] = svc_model(cfg, svc)
    url = svc_base(cfg, svc).rstrip("/") + "/v1/messages"
    hdr = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    if not stream:
        r = requests.post(url, headers=hdr, json=body, timeout=240)
        if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
        j = r.json()
        text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        calls = [{"id": b.get("id", ""), "type": "function",
                  "function": {"name": b.get("name", ""), "arguments": json.dumps(b.get("input") or {}, ensure_ascii=False)}}
                 for b in j.get("content", []) if b.get("type") == "tool_use"]
        return {"content": text, "tool_calls": calls}
    r = requests.post(url, headers=hdr, json={**body, "stream": True}, timeout=(15, 240), stream=True)
    if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    content, calls = "", {}
    try:
        for raw in r.iter_lines():
            if not raw: continue
            line = raw.decode("utf-8", "ignore")
            if not line.startswith("data:"): continue
            try: j = json.loads(line[5:].strip())
            except Exception: continue
            if j.get("type") == "error": raise RuntimeError(str(j.get("error"))[:300])
            if j.get("type") == "content_block_start":
                b = j.get("content_block") or {}
                if b.get("type") == "tool_use":
                    calls[j.get("index", 0)] = {"id": b.get("id", ""), "type": "function",
                                                "function": {"name": b.get("name", ""), "arguments": ""}}
            elif j.get("type") == "content_block_delta":
                d = j.get("delta") or {}
                if d.get("type") == "text_delta" and d.get("text"):
                    content += d["text"]
                    if on_delta: on_delta(content)
                elif d.get("type") == "input_json_delta":
                    ci = calls.get(j.get("index", 0))
                    if ci is not None: ci["function"]["arguments"] += d.get("partial_json", "")
    finally: r.close()
    return {"content": content, "tool_calls": [calls[i] for i in sorted(calls)]}

def fetch_models(cfg, svc):
    """Список id моделей обраного сервісу (для вибору й пошуку в налаштуваннях). Викликається у фоні."""
    S = CLOUD_SERVICES[svc]; key = svc_key(cfg, svc)
    if svc == "google":
        if not key: raise RuntimeError(T("Введи ключ Google API — тоді підвантажу список моделей."))
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key}, timeout=20)
        if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
        ids = [m.get("name", "").split("/")[-1] for m in r.json().get("models", [])
               if "generateContent" in (m.get("supportedGenerationMethods") or ["generateContent"])]
        return sorted(ids)
    if not key: raise RuntimeError(T("Введи API-ключ — тоді підвантажу список моделей."))
    if S["kind"] == "anthropic":
        r = requests.get(svc_base(cfg, svc).rstrip("/") + "/v1/models", timeout=20,
                         headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
        if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
        return sorted(m.get("id", "") for m in r.json().get("data", []) if m.get("id"))
    r = requests.get(svc_base(cfg, svc).rstrip("/") + "/models", timeout=20, headers={"Authorization": "Bearer " + key})
    if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return sorted(m.get("id", "") for m in r.json().get("data", []) if m.get("id"))

class ModelFetcher(QThread):
    """Тягне список моделей у фоні, щоб налаштування не зависали."""
    done = pyqtSignal(str, list, str)
    def __init__(self, cfg, svc):
        super().__init__(); self.cfg, self.svc = cfg, svc
    def run(self):
        try: self.done.emit(self.svc, fetch_models(self.cfg, self.svc), "")
        except Exception as e: self.done.emit(self.svc, [], str(e))

def endpoint(cfg, vision=False):
    svc = api_provider(cfg); S = CLOUD_SERVICES.get(svc)
    if S and S["kind"] != "google" and cfg.get("provider") == "cloud":
        key = svc_key(cfg, svc)
        if not key: raise RuntimeError(f"Немає ключа {S['title']} — відкрий налаштування (шестерня) і встав його.")
        if S["kind"] == "anthropic":
            return svc_base(cfg, svc).rstrip("/") + "/v1/messages", svc_model(cfg, svc), {"x-api-key": key, "anthropic-version": "2023-06-01"}
        hdr = {"Authorization": "Bearer " + key}
        hdr.update(S.get("extra") or {})
        return svc_base(cfg, svc).rstrip("/") + "/chat/completions", svc_model(cfg, svc), hdr
    if cfg["local_backend"] == "lmstudio":
        base = cfg["lmstudio_url"].rstrip("/")
        model = ((cfg.get("lmstudio_vision_model") or "").strip() if vision else "") or cfg.get("_lms_resolved_model") or (cfg["local_model"] or "local")
        return base + "/chat/completions", model, {}
    port = int(cfg["llama_port"]) + (1 if vision and (cfg.get("llama_vision_model") or "").strip() else 0)
    return f"http://127.0.0.1:{port}/v1/chat/completions", cfg["local_model"] or "local", {}

def llm_chat(cfg, messages, tools=None, vision=False):
    svc = api_provider(cfg)
    if svc == "google": return google_generate(cfg, messages, tools, stream=False)
    if CLOUD_SERVICES.get(svc, {}).get("kind") == "anthropic": return anthropic_generate(cfg, messages, tools, stream=False)
    url, model, hdr = endpoint(cfg, vision)
    body = {"model": model, "messages": messages, "temperature": .8}
    if tools: body["tools"], body["tool_choice"] = tools, "auto"
    r = requests.post(url, headers=hdr, json=body, timeout=240)
    if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]

def llm_stream(cfg, messages, tools, on_delta, vision=False):
    """SSE-стрімінг: текст іде в UI одразу, tool_calls збираються по шматках."""
    svc = api_provider(cfg)
    if svc == "google": return google_generate(cfg, messages, tools, on_delta, stream=True)
    if CLOUD_SERVICES.get(svc, {}).get("kind") == "anthropic": return anthropic_generate(cfg, messages, tools, on_delta, stream=True)
    url, model, hdr = endpoint(cfg, vision)
    body = {"model": model, "messages": messages, "temperature": .8, "stream": True}
    if tools: body["tools"], body["tool_choice"] = tools, "auto"
    r = requests.post(url, headers=hdr, json=body, timeout=(15, 240), stream=True)
    if r.status_code != 200: raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    content, calls = "", {}
    for raw in r.iter_lines():
        if not raw: continue
        line = raw.decode("utf-8", "ignore")
        if not line.startswith("data:"): continue
        data = line[5:].strip()
        if data == "[DONE]": break
        try: j = json.loads(data)
        except Exception: continue
        if j.get("error"): raise RuntimeError(str(j["error"])[:300])
        ch = j.get("choices") or []
        if not ch: continue
        d = ch[0].get("delta") or {}
        if d.get("content"): content += d["content"]; on_delta(content)
        for tc in d.get("tool_calls") or []:
            c = calls.setdefault(tc.get("index", 0), {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
            if tc.get("id"): c["id"] = tc["id"]
            fnc = tc.get("function") or {}
            if fnc.get("name"): c["function"]["name"] += fnc["name"]
            if fnc.get("arguments"): c["function"]["arguments"] += fnc["arguments"]
    return {"content": content, "tool_calls": [calls[i] for i in sorted(calls)]}

# СИСТЕМНІ ПРОМТИ — у prompts.json поруч зі скриптом: повні варіанти uk/ru/en
# (значення однакове, різниця лише в мові). Мова відповідей моделі = мова з налаштувань:
# з файла береться саме той варіант промту, і модель жорстко його тримає.
# Файл перечитується перед кожною відповіддю — правки набирають чинності одразу.
PROMPTS_PATH = Path(__file__).with_name("prompts.json")
_PROMPTS_GOOD = {}
def get_prompts():
    """Промти з prompts.json; якщо файл відсутній/пошкоджений — останній вдалий зчиток або мінімальний запасний."""
    global _PROMPTS_GOOD
    try:
        data = json.loads(PROMPTS_PATH.read_text("utf-8"))
        if {"uk", "ru", "en"} <= set(data):
            _PROMPTS_GOOD = {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}
            return _PROMPTS_GOOD
    except Exception:
        pass
    return _PROMPTS_GOOD or PROMPTS_FALLBACK
def P(key=None, lang=None):
    """Варіант промтів для мови з налаштувань (або конкретної); key — окреме поле чи весь словник."""
    pr = get_prompts().get(lang or LANG) or get_prompts()["uk"]
    return pr if key is None else pr.get(key)

# мінімальний запасний варіант — лише якщо prompts.json загубився, щоб Лура працювала і без нього
PROMPTS_FALLBACK = {
    "uk": {"persona": "Ти — Лура, цифрова супутниця з характером. Відповідай коротко (1–2 речення), жваво, жартуй. "
                      "На початку відповіді став тег емоції [[happy]]. Попросили щось відкрити/зробити — ОДРАЗУ викликай "
                      "інструмент, короткий підсумок після. (Файл prompts.json не знайдено — це спрощений промт.)",
           "profile": "Зараз: {now}; ОС: {os}. Ім'я: {user}.\n{facts}\n{prefs}\nНагадування:\n{rem}",
           "lang_rule": "МОВА ВІДПОВІДІ: Українська. ВСЮ відповідь — ТІЛЬКИ українською.",
           "greeting_styles": ["коротке й миле"],
           "note_greeting": "Користувач щойно запустив тебе. Привітайся коротко.", "note_reminder": "Нагадай: «{text}».",
           "note_proactive": "Можеш коротко написати користувачу першій; нічого нема — лише [[skip]].",
           "word_reminder": "Нагадування", "svc_mark": "[службове] ",
           "style_modifiers": {"header": "ХАРАКТЕР", "restrained": "стримано.", "bright": "яскраво.",
                               "lively": "живо.", "sarcasm_on": "сарказм можна.", "sarcasm_off": "без сарказму.",
                               "hurt_on": "можеш образитися.", "hurt_off": "не ображайся.", "name": "звертайся на ім'я {name}."},
           "misc": {"pro_active": "так", "pro_off": "НІ", "yes": "так", "no": "ні", "no_name": "(невідоме)",
                    "no_facts": "(-)", "no_prefs": "(-)", "no_cmds": "(-)", "no_rems": "(-)"}},
    "ru": {"persona": "Ты — Лура, цифровая спутница с характером. Отвечай коротко (1–2 предложения), живо, шути. "
                      "В начале ответа ставь тег эмоции [[happy]]. Попросили что-то открыть/сделать — СРАЗУ вызывай "
                      "инструмент, короткий итог после. (Файл prompts.json не найден — это упрощённый промпт.)",
           "profile": "Сейчас: {now}; ОС: {os}. Имя: {user}.\n{facts}\n{prefs}\nНапоминания:\n{rem}",
           "lang_rule": "ЯЗЫК ОТВЕТА: Русский. ВЕСЬ ответ — ТОЛЬКО по-русски.",
           "greeting_styles": ["короткое и милое"],
           "note_greeting": "Пользователь только что запустил тебя. Поздоровайся коротко.", "note_reminder": "Напомни: «{text}».",
           "note_proactive": "Можешь коротко написать пользователю первой; нечего — только [[skip]].",
           "word_reminder": "Напоминание", "svc_mark": "[служебное] ",
           "style_modifiers": {"header": "ХАРАКТЕР", "restrained": "сдержанно.", "bright": "ярко.",
                               "lively": "живо.", "sarcasm_on": "сарказм можно.", "sarcasm_off": "без сарказма.",
                               "hurt_on": "можешь обидеться.", "hurt_off": "не обижайся.", "name": "обращайся по имени {name}."},
           "misc": {"pro_active": "да", "pro_off": "НЕТ", "yes": "да", "no": "нет", "no_name": "(неизвестно)",
                    "no_facts": "(-)", "no_prefs": "(-)", "no_cmds": "(-)", "no_rems": "(-)"}},
    "en": {"persona": "You are Lura, a digital companion with character. Answer briefly (1–2 sentences), lively, joke. "
                      "Start replies with an emotion tag like [[happy]]. Asked to open/do something — CALL the tool "
                      "IMMEDIATELY, short summary after. (prompts.json not found — this is a simplified prompt.)",
           "profile": "Now: {now}; OS: {os}. Name: {user}.\n{facts}\n{prefs}\nReminders:\n{rem}",
           "lang_rule": "RESPONSE LANGUAGE: English. The WHOLE reply must be in English ONLY.",
           "greeting_styles": ["short and sweet"],
           "note_greeting": "The user has just launched you. Greet them briefly.", "note_reminder": "Remind: «{text}».",
           "note_proactive": "You may write a short message first; nothing to say — just [[skip]].",
           "word_reminder": "Reminder", "svc_mark": "[system] ",
           "style_modifiers": {"header": "CHARACTER", "restrained": "reserved.", "bright": "bright.",
                               "lively": "lively.", "sarcasm_on": "sarcasm ok.", "sarcasm_off": "no sarcasm.",
                               "hurt_on": "may take offense.", "hurt_off": "don't take offense.", "name": "use the name {name}."},
           "misc": {"pro_active": "yes", "pro_off": "NO", "yes": "yes", "no": "no", "no_name": "(unknown)",
                    "no_facts": "(-)", "no_prefs": "(-)", "no_cmds": "(-)", "no_rems": "(-)"}},
}

SYS_RE = re.compile(r"\[\s*(?:СИСТЕМА|СИСТЕМНЕ|система|system|службове|службов|служебн)[^\]]*\]\s*", re.I)
FILETAG_RE = re.compile(r"\[\s*файл\s*:[^\]]*\]\s*", re.I)
TAG = re.compile(r"\[\[(.+?)\]\]", re.S)
def split_tags(text):
    text = SYS_RE.sub("", FILETAG_RE.sub("", re.sub(r"(?is)<think>.*?</think>", "", text))); out, ev, last = "", [], 0
    for m in TAG.finditer(text):
        out += text[last:m.start()]; ev.append((len(out), m.group(1))); last = m.end()
    out += text[last:]; lead = len(out) - len(out.lstrip())
    return out.strip(), [(max(0, i - lead), s) for i, s in ev]
def partial_plain(raw):
    """Для стрімінгу: ховаємо недописані теги [[..., <think>... і службові позначки."""
    raw = re.sub(r"(?is)<think>.*?</think>", "", raw); i = raw.lower().rfind("<think>")
    if i != -1: raw = raw[:i]
    i = raw.rfind("[[")
    if i != -1 and "]]" not in raw[i:]: raw = raw[:i]
    if raw.endswith("["): raw = raw[:-1]
    if re.match(r"^\s*\[[^\]]{0,14}$", raw): raw = ""
    return split_tags(raw)

def msg_has_image(msgs):
    for m in msgs:
        c = m.get("content")
        if isinstance(c, list) and any(isinstance(i, dict) and i.get("type") == "image_url" for i in c): return True
    return False

def _msg_tokens(m):
    c = m.get("content", "")
    if isinstance(c, str): return len(c) // 4 + (260 if m.get("tool_calls") else 6)
    t = 6
    for it in c:
        if isinstance(it, dict):
            if it.get("type") == "image_url": t += 1600
            else: t += len(str(it.get("text", ""))) // 4
    return t

def trim_msgs_for_context(cfg, msgs, tools):
    """Локальні сервери мають жорсткий ліміт контексту — обрізаємо найстарішу частину діалогу,
    щоб запит помістився (системний промт і останні репліки залишаються)."""
    if cfg.get("provider") != "local": return msgs
    ctx = int(cfg["llama_ctx"]) if cfg.get("local_backend") == "llamacpp" else 8192
    budget = max(1200, ctx - 3600 - (2600 if tools else 0))   # запас на промти, схему інструментів і відповідь
    sys_msgs = [m for m in msgs if m.get("role") == "system"]
    rest = [m for m in msgs if m.get("role") != "system"]
    total = sum(_msg_tokens(m) for m in sys_msgs); i = 0
    while len(rest) - i > 2:
        if total + sum(_msg_tokens(m) for m in rest[i:]) <= budget: break
        total += _msg_tokens(rest[i]); i += 1
        while i < len(rest) and rest[i].get("role") != "user":   # не відрізаємо tool-виклики від їх результатів
            total += _msg_tokens(rest[i]); i += 1
    return sys_msgs + rest[i:] if i else msgs

class Worker(QThread):
    status = pyqtSignal(str); delta = pyqtSignal(str); newround = pyqtSignal(); ok = pyqtSignal(str); err = pyqtSignal(str)
    def __init__(self, app, history, content):
        super().__init__(); self.app, self.history, self.content = app, history, content
    def run(self):
        try:
            tools = self.app.tools
            msgs = [{"role": "system", "content": self.app.build_system()}] + self.history + [{"role": "user", "content": self.content}]
            cap = 4000 if self.app.cfg.get("provider") == "local" else 12000   # локальним моделям — коротші результати інструментів
            last_tool = None
            for _ in range(10):
                msgs = trim_msgs_for_context(self.app.cfg, msgs, TOOLS)
                self.newround.emit(); got = [False]
                def cb(raw): got[0] = True; self.delta.emit(raw)
                vision = msg_has_image(msgs)
                if vision and not self.app.server.ensure_vision():
                    raise RuntimeError("не вдалось запустити vision-модель — перевір шлях до неї у налаштуваннях")
                try: m = llm_stream(self.app.cfg, msgs, TOOLS, cb, vision=vision)
                except Exception:
                    if got[0] or api_provider(self.app.cfg) == "google": raise
                    m = llm_chat(self.app.cfg, msgs, TOOLS, vision=vision)       # запасний варіант без стрімінгу
                calls = m.get("tool_calls") or []
                if not calls:
                    txt = (m.get("content") or "").strip()
                    if not txt and last_tool:      # модель мовчить після дій — коротко кажемо самі
                        fl = FEEDBACK_LINES.get(LANG, FEEDBACK_LINES["uk"])
                        txt = random.choice(fl.get(last_tool, fl["*"]))
                    self.ok.emit(txt); return
                msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
                for c in calls:
                    f = c["function"]
                    try: args = json.loads(f.get("arguments") or "{}")
                    except Exception: args = {}
                    last_tool = f["name"]
                    self.status.emit(tool_label(last_tool) + "…")
                    msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": tools.run(last_tool, args)[:cap]})
                if tools.images:
                    cont = [{"type": "text", "text": T("Ось скріншот екрана:")}] + [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b}} for b in tools.images]
                    msgs.append({"role": "user", "content": cont}); tools.images = []
            self.ok.emit("[[confused]] " + T("Я трохи заплуталась — забагато кроків. Спробуємо ще раз?"))
        except Exception as ex: self.err.emit(str(ex))

# ═══════════════════════ ЛОКАЛЬНИЙ СЕРВЕР (llama.cpp / LM Studio) ═══════════════════════
class LocalServer(QObject):
    """Сам запускає llama-server без вікна консолі; прогрес іде в рядок статусу внизу чату."""
    msg = pyqtSignal(str)
    def __init__(self, app): super().__init__(); self.app = app; self.proc = None; self.vproc = None; self.gen = 0; self.last = ""; self.spawn_lock = threading.Lock()
    def ensure(self):
        self.gen += 1; g = self.gen; c = self.app.cfg
        if c["provider"] != "local" or c["local_backend"] != "llamacpp": self.stop()
        if c["provider"] != "local": self.msg.emit(""); return
        threading.Thread(target=self._llama if c["local_backend"] == "llamacpp" else self._lms, args=(g,), daemon=True).start()
    def stop(self):
        for attr in ("proc", "vproc"):
            p = getattr(self, attr); setattr(self, attr, None)
            if p and p.poll() is None:
                def kill(p=p):
                    try: p.terminate(); p.wait(6)
                    except Exception:
                        try: p.kill()
                        except Exception: pass
                threading.Thread(target=kill, daemon=True).start()
    def stop_now(self):
        for attr in ("proc", "vproc"):
            p = getattr(self, attr); setattr(self, attr, None)
            if p and p.poll() is None:
                try: p.terminate(); p.wait(3)
                except Exception: pass
    def _flash(self, text, g, sec=4):
        self.msg.emit(text); time.sleep(sec)
        if g == self.gen: self.msg.emit("")
    def _reader(self, proc):
        for line in iter(proc.stdout.readline, b""):
            t = line.decode("utf-8", "ignore").strip()
            if t: self.last = t
    @staticmethod
    def _alive(base):
        try: return requests.get(base + "/health", timeout=1.5).status_code == 200
        except Exception: return False
    def _llama(self, g):
        c = self.app.cfg; port = int(c["llama_port"]); base = f"http://127.0.0.1:{port}"
        if self._alive(base): self._flash("llama.cpp уже працює", g, 3); return
        if not c["llama_autostart"]: self._flash("llama.cpp не запущено (автозапуск вимкнено)", g, 5); return
        proc = self._spawn_llama(c, port, c["llama_model_path"], "llama.cpp")
        if proc is not None: self._wait_llama(proc, base, "llama.cpp", g)
    def _spawn_llama(self, c, port, model_path, label):
        exe = c["llama_exe"].strip().strip('"') or shutil.which("llama-server") or ""
        if not exe or not (Path(exe).exists() or shutil.which(exe)): self._flash(T("вкажи llama-server у налаштуваннях"), self.gen, 6); return None
        model = (model_path or "").strip().strip('"')
        if not model or not Path(model).exists(): self._flash(T("вкажи файл моделі .gguf для «{label}» у налаштуваннях").replace("{label}", label), self.gen, 6); return None
        cmd = [exe, "-m", model, "--port", str(int(port)), "--jinja", "-c", str(int(c["llama_ctx"])), "-ngl", str(int(c["llama_ngl"]))]
        try: cmd += shlex.split(c["llama_args"], posix=not IS_WIN)
        except ValueError: pass
        kw = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        if IS_WIN: kw["creationflags"] = 0x08000000        # CREATE_NO_WINDOW — жодної консолі
        if Path(exe).exists(): kw["cwd"] = str(Path(exe).parent)
        self.msg.emit(T("запускаю {label}…").replace("{label}", label))
        with self.spawn_lock:
            main = int(port) == int(c["llama_port"])
            cur = self.proc if main else self.vproc
            if cur is not None and cur.poll() is None: return cur      # вже запущений — просто чекаємо
            try: proc = subprocess.Popen(cmd, **kw)
            except Exception as ex: self._flash(T("не вдалось запустити: {err}").replace("{err}", str(ex)), self.gen, 8); return None
            if main: self.proc = proc
            else: self.vproc = proc
            threading.Thread(target=self._reader, args=(proc,), daemon=True).start()
            return proc
    def _wait_llama(self, proc, base, label, g, timeout=900):
        t0 = time.time()
        while g == self.gen and time.time() - t0 < timeout:
            if proc.poll() is not None: self._flash(T("{label} зупинився: {err}").replace("{label}", label).replace("{err}", self.last[:70]), g, 10); return False
            if self._alive(base): self._flash(T("{label} готовий").replace("{label}", label), g, 3); return True
            self.msg.emit(T("{label}: завантажую модель… {n} с").replace("{label}", label).replace("{n}", str(int(time.time() - t0)))); time.sleep(1)
        return False
    def ensure_vision(self):
        """llama.cpp: якщо вказано окрему vision-модель, піднімає її сервер на порт+1.
        Викликається з потоку Worker, тому може блокуватись, поки модель вантажиться."""
        c = self.app.cfg
        if c.get("provider") != "local" or c.get("local_backend") != "llamacpp": return True
        path = (c.get("llama_vision_model") or "").strip().strip('"')
        if not path: return True                      # окремої vision-моделі нема — зображення йдуть основній
        port = int(c["llama_port"]) + 1; base = f"http://127.0.0.1:{port}"
        if self._alive(base): return True
        if not Path(path).exists():
            self.msg.emit(T("не знайшла файл vision-моделі — перевір шлях у налаштуваннях")); return False
        proc = self._spawn_llama(c, port, path, T("vision-модель"))
        if proc is None: return False
        return self._wait_llama(proc, base, T("vision-модель"), self.gen)
    @staticmethod
    def _lms_models(url):
        try:
            r = requests.get(url + "/models", timeout=2)
            if r.status_code != 200: return None
            return [str(m.get("id", "")) for m in (r.json().get("data") or [])]
        except Exception: return None
    def _lms(self, g):
        c = self.app.cfg; url = c["lmstudio_url"].rstrip("/")
        got = self._lms_models(url)
        if got is None:      # LM Studio — усе вручну: сервер і модель вмикає лише користувач
            self._flash(T("LM Studio не запущено — запусти сервер у LM Studio (вкладка Developer)"), g, 8); return
        self._lms_check_model(c, got, g)
    def _lms_check_model(self, c, got, g):
        """Лура нічого не запускає і не завантажує в LM Studio — лише перевіряє, чи на місці модель,
        і підказує. Шлях у налаштуваннях автоматично звіряється з id завантаженої моделі."""
        want = (c.get("local_model") or "").strip()
        def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).casefold())
        w, ws = norm(want), norm(Path(want).stem) if want else ""
        hit = next((i for i in got or [] if i and (norm(i) == w or norm(i) == ws or (w and norm(i) in w) or (ws and ws in norm(i)))), None)
        c["_lms_resolved_model"] = hit          # id запам'ятовуємо, лише коли модель справді завантажена
        if not want or hit: self._flash(T("LM Studio готовий"), g, 3); return
        ids_hint = ", ".join(got[:6]) or T("жодної")
        self._flash(T("LM Studio: модель «{name}» не завантажена — увімкни її у LM Studio. Завантажені: {ids}").replace("{name}", Path(want).name).replace("{ids}", ids_hint), g, 10)

# ═══════════════════════════════════ UI ═══════════════════════════════════
def qss():
    return f"""QDialog,QMessageBox{{background:{TH['dlg']};color:{TH['fg']}}}QLabel{{color:{TH['fg']}}}
QPushButton{{background:{TH['acc']};color:#fff;border:none;border-radius:8px;padding:6px 12px}}
QPushButton#chip{{background:{rgba(TH['btn'])};color:{TH['fg']};border:1px solid {TH['dlgb']};border-radius:13px;padding:5px 8px;font-weight:600}}
QPushButton#chip:hover{{background:{rgba(TH['btnh'])}}}
QPushButton#chip:checked{{background:{TH['acc']};color:#fff;border-color:{TH['acc']}}}
QMenu{{background:{TH['dlg']};color:{TH['fg']};border:1px solid {TH['dlgb']}}}QMenu::item{{padding:5px 18px}}QMenu::item:selected{{background:{TH['acc']};color:#fff}}
QScrollBar:vertical{{background:{rgba((*TH['border'], 35))};width:12px;margin:5px 2px;border-radius:6px}}
QScrollBar::handle:vertical{{background:{rgba((*TH['border'], 190))};min-height:38px;border-radius:5px;border:1px solid {rgba((*TH['line'], 110))}}}
QScrollBar::handle:vertical:hover{{background:{TH['acc']}}}
QScrollBar::add-line,QScrollBar::sub-line{{height:0;border:none}}
QScrollBar::add-page,QScrollBar::sub-page{{background:transparent}}"""

class Fade(QWidget):
    """М'яке розмиття під шапкою: повідомлення плавно розчиняються під обличчям."""
    def __init__(self, win, parent):
        super().__init__(parent); self.win = win; self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    def paintEvent(self, _):
        w, h = self.width(), self.height()
        if w < 2 or h < 2: return
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied); img.fill(0)
        off = self.mapTo(self.win, QPoint(0, 0))
        q = QPainter(img); q.setRenderHint(QPainter.RenderHint.Antialiasing); q.translate(-off.x(), -off.y()); self.win.paint_bg(q); q.resetTransform()
        q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        g = QLinearGradient(0, 0, 0, h); g.setColorAt(0, QColor(0, 0, 0, 255)); g.setColorAt(.5, QColor(0, 0, 0, 225)); g.setColorAt(1, QColor(0, 0, 0, 0))
        q.fillRect(img.rect(), QBrush(g)); q.end(); QPainter(self).drawImage(0, 0, img)

class ChatPage(QWidget):
    def paintEvent(self, _):
        # Keep the chat background in sync with the parent as its emotion glow changes.
        owner = getattr(self, "owner", None)
        if owner is None: return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        off = self.mapTo(owner, QPoint(0, 0)); p.translate(-off.x(), -off.y())
        owner.paint_bg(p); p.end()
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "drop_hint"): self.drop_hint.setGeometry(self.rect())
        if hasattr(self, "fade"): self.fade.setGeometry(0, 0, self.width(), 50); self.fade.raise_()

class Input(QPlainTextEdit):
    send = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        # Компактне поле вводу не має показувати внутрішній рожевий повзунок прокрутки.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier): self.send.emit(); return
        super().keyPressEvent(e)

class Typing(QWidget):
    """Анімована бульбашка набору з трьома крапками."""
    def __init__(self):
        super().__init__(); self.setFixedSize(58, 34); self.started = time.monotonic()
        self.clock = QTimer(self); self.clock.timeout.connect(self.update); self.clock.start(40)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(*TH["bub"])); p.drawRoundedRect(QRectF(self.rect()), 17, 17)
        now = time.monotonic() - self.started
        for i in range(3):
            phase = now * 5 - i * .8
            alpha = .35 + .65 * (.5 + .5 * math.sin(phase))
            color = QColor(*TH["line"]); color.setAlphaF(alpha)
            p.setBrush(color); p.drawEllipse(QPointF(17 + i * 12, 17 - 2 * math.sin(phase)), 3.4, 3.4)
        p.end()

class Toast(QLabel):
    clicked = pyqtSignal()
    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWordWrap(True); self.setMaximumWidth(280); self.setTextFormat(Qt.TextFormat.RichText); self.restyle()
        self.t = QTimer(self); self.t.setSingleShot(True); self.t.timeout.connect(self.hide)
    def restyle(self):
        self.setStyleSheet(f"background:{TH['dlg']};color:{TH['fg']};border:1px solid {TH['dlgb']};border-radius:14px;padding:10px 12px;")
        self.setFont(ufont(14))
    def pop(self, text, anchor):
        self.setText(to_html(text[:260])[0]); self.adjustSize()
        x = anchor.left() - self.width() - 8
        if x < 0: x = anchor.right() + 8
        self.move(x, max(0, anchor.top())); self.show(); self.t.start(8000)
    def mousePressEvent(self, e): self.hide(); self.clicked.emit()

class SettingsPage(QScrollArea):
    """Налаштування всередині вікна (плавно в'їжджають замість чату)."""
    def __init__(self, app, parent):
        super().__init__(parent); self.app = app; self.edits = []; self.setMouseTracking(True)
        self.setWidgetResizable(True); self.setFrameShape(QFrame.Shape.NoFrame); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False); self.inner = QWidget(); self.inner.setObjectName("inner"); self.setWidget(self.inner)
        self.v = QVBoxLayout(self.inner); self.v.setContentsMargins(10, 24, 10, 16); self.v.setSpacing(12)
        self.fade = Fade(app, self); self.build(); self.restyle()
    def resizeEvent(self, e):
        super().resizeEvent(e); self.fade.setGeometry(0, 0, self.width(), 34); self.fade.raise_()
    # ── будівельні цеглинки
    def card(self, title):
        f = QFrame(); f.setObjectName("card"); l = QVBoxLayout(f); l.setContentsMargins(14, 12, 14, 14); l.setSpacing(9)
        t = QLabel(T(title)); t.raw_text = title; t.setObjectName("ctitle"); l.addWidget(t); self.v.addWidget(f); return l
    def label(self, text):
        l = QLabel(T(text)); l.raw_text = text; l.setObjectName("clab"); l.setWordWrap(True); return l
    def edit(self, key, ph="", pw=False, num=False, width=None):
        le = QLineEdit(str(self.app.cfg.get(key, ""))); le.raw_placeholder = ph; le.setPlaceholderText(T(ph)); le.setMouseTracking(True)
        if pw: le.setEchoMode(QLineEdit.EchoMode.Password)
        if width: le.setFixedWidth(width)
        le.editingFinished.connect(lambda: self.commit_one(key, le, num)); self.edits.append((key, le, num)); return le
    def commit_one(self, key, le, num):
        v = le.text().strip()
        if num:
            try: v = int(v)
            except ValueError: v = DEFAULT_CFG[key]; le.setText(str(v))
        old = self.app.cfg.get(key)
        self.app.cfg[key] = v; jsave(CFG_P, self.app.cfg)
        if key == "local_model" and v and v != old and self.app.cfg.get("provider") == "local" and self.app.cfg.get("local_backend") == "lmstudio":
            self.app.server.ensure()      # назву моделі справді змінили — тоді пробуємо завантажити іншу
    def field(self, text, key, **kw):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(4); l.addWidget(self.label(text)); l.addWidget(self.edit(key, **kw)); return w
    def path_field(self, text, key, ph, folder=False, flt=""):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(4); l.addWidget(self.label(text))
        r = QHBoxLayout(); r.setSpacing(6); le = self.edit(key, ph); b = QPushButton("…"); b.setObjectName("browse"); b.setFixedSize(36, 32)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        def pick():
            d = QFileDialog.getExistingDirectory(self, text, le.text()) if folder else QFileDialog.getOpenFileName(self, text, le.text(), flt)[0]
            if d: le.setText(d); self.commit_one(key, le, False)
        b.clicked.connect(pick); r.addWidget(le, 1); r.addWidget(b); l.addLayout(r); return w
    def row(self, text, widget):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.addWidget(self.label(text), 1); l.addWidget(widget); return w
    def switch(self, text, key, cb=None):
        sw = Switch(bool(self.app.cfg[key]))
        def ch(v):
            self.app.cfg[key] = v; jsave(CFG_P, self.app.cfg)
            if cb: cb()
        sw.toggled.connect(ch); return self.row(text, sw)
    # ── сторінка
    def build(self):
        c = self.app.cfg
        l = self.card("Модель"); self.prov = Segmented([T("API-хмара"), T("Локальна")], 0 if c.get("provider", "cloud") == "cloud" else 1)
        self.prov.changed.connect(lambda i: self.app.set_provider("cloud" if i == 0 else "local")); l.addWidget(self.prov)
        self.g_cloud = QWidget(); gc = QVBoxLayout(self.g_cloud); gc.setContentsMargins(0, 0, 0, 0); gc.setSpacing(9)
        # другий крок: вибір сервісу — сітка «чіпів», щоб УСІ сервіси були видні й вміщалися
        from PyQt6.QtWidgets import QGridLayout
        self.svc_grid = QWidget(); gl = QGridLayout(self.svc_grid); gl.setContentsMargins(0, 0, 0, 0); gl.setSpacing(6)
        self.svc_btns = {}
        for i, (sid, S) in enumerate(CLOUD_SERVICES.items()):
            b = QPushButton(S.get("short", S["title"])); b.setObjectName("chip"); b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=sid: self.app.set_cloud_provider(s))
            gl.addWidget(b, i // 2, i % 2)
            self.svc_btns[sid] = b
        gc.addWidget(self.svc_grid)
        # ключ обраного сервісу (пишемо в cfg.api_keys[svc])
        self.key_label = QLabel(); self.key_edit = QLineEdit(); self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.editingFinished.connect(self.commit_key)
        kw = QWidget(); kl = QVBoxLayout(kw); kl.setContentsMargins(0, 0, 0, 0); kl.setSpacing(4)
        kl.addWidget(self.key_label); kl.addWidget(self.key_edit); gc.addWidget(kw)
        # адреса сервісу — редагована для DarkerAPI/Користувацького
        self.base_label = QLabel(); self.base_edit = QLineEdit(); self.base_edit.editingFinished.connect(self.commit_base)
        bw = QWidget(); bl = QVBoxLayout(bw); bl.setContentsMargins(0, 0, 0, 0); bl.setSpacing(4)
        bl.addWidget(self.base_label); bl.addWidget(self.base_edit); gc.addWidget(bw); self.base_box = bw
        # файли ключів Google (ротація)
        # модель: комбобокс із пошуком + кнопка оновлення списку з API сервісу
        mr = QWidget(); ml = QVBoxLayout(mr); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(4)
        self.model_label = QLabel(); ml.addWidget(self.model_label)
        r = QHBoxLayout(); r.setSpacing(6)
        self.model_combo = QComboBox(); self.model_combo.setEditable(True); self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_combo.setMinimumWidth(240)
        comp = QCompleter([]); comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)      # пошук моделі — по будь-якій частині назви
        self.model_combo.setCompleter(comp)
        self.model_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.model_combo.currentIndexChanged.connect(self.commit_model)
        self.model_combo.lineEdit().editingFinished.connect(self.commit_model)
        self.model_btn = QPushButton("⟳"); self.model_btn.setObjectName("browse"); self.model_btn.setFixedSize(36, 32)
        self.model_btn.setCursor(Qt.CursorShape.PointingHandCursor); self.model_btn.setToolTip(T("Оновити список моделей"))
        self.model_btn.clicked.connect(self.refresh_models)
        r.addWidget(self.model_combo, 1); r.addWidget(self.model_btn); ml.addLayout(r)
        self.model_hint = QLabel(""); self.model_hint.setObjectName("clab"); self.model_hint.setWordWrap(True)
        ml.addWidget(self.model_hint); gc.addWidget(mr)
        self.fill_service_ui()
        l.addWidget(self.g_cloud)
        self.g_loc = QWidget(); g = QVBoxLayout(self.g_loc); g.setContentsMargins(0, 0, 0, 0); g.setSpacing(9)
        g.addWidget(self.label("Який локальний сервер")); self.backend = Segmented(["llama.cpp", "LM Studio"], 0 if c["local_backend"] == "llamacpp" else 1)
        self.backend.changed.connect(lambda i: self.app.set_backend("llamacpp" if i == 0 else "lmstudio")); g.addWidget(self.backend)
        self.g_llama = QWidget(); gl = QVBoxLayout(self.g_llama); gl.setContentsMargins(0, 0, 0, 0); gl.setSpacing(9)
        gl.addWidget(self.path_field("Файл llama-server", "llama_exe", "C:\\llama.cpp\\llama-server.exe", flt="Програми (*.exe);;Усі файли (*)"))
        gl.addWidget(self.path_field("Модель (.gguf)", "llama_model_path", "C:\\models\\model.gguf", flt="GGUF (*.gguf);;Усі файли (*)"))
        gl.addWidget(self.path_field("Vision-модель (.gguf), не обов'язково", "llama_vision_model", "C:\\models\\vision.gguf", flt="GGUF (*.gguf);;Усі файли (*)"))
        gl.addWidget(self.label("Не обов'язково: окрема модель, що вміє бачити скріншоти. Порожньо — екран бачить основна модель."))
        gl.addWidget(self.row("Порт", self.edit("llama_port", num=True, width=90))); gl.addWidget(self.row("Контекст (токенів)", self.edit("llama_ctx", num=True, width=90)))
        gl.addWidget(self.row("Шарів на GPU (-ngl)", self.edit("llama_ngl", num=True, width=90))); gl.addWidget(self.field("Додаткові аргументи", "llama_args", ph="--flash-attn -t 8"))
        gl.addWidget(self.switch("Запускати сервер автоматично", "llama_autostart"))
        gl.addWidget(self.label("Сервер стартує сам, коли обираєш «Локальна», без вікна консолі. Прогрес — внизу чату.")); g.addWidget(self.g_llama)
        self.g_lms = QWidget(); gm = QVBoxLayout(self.g_lms); gm.setContentsMargins(0, 0, 0, 0); gm.setSpacing(9)
        gm.addWidget(self.field("Адреса LM Studio", "lmstudio_url", ph="http://127.0.0.1:1234/v1"))
        gm.addWidget(self.field("Модель LM Studio (не обов'язково)", "local_model", ph="назва або шлях до моделі"))
        gm.addWidget(self.label("LM Studio — усе вручну: Лура не запускає ні сервер, ні модель. Увімкни їх у LM Studio сам; llama.cpp запускається автоматично."))
        gm.addWidget(self.label("Не обов'язково: модель зі списку LM Studio, яку має використовувати Лура. Порожньо — та, що завантажена."))
        gm.addWidget(self.field("Назва vision-моделі (не обов'язково)", "lmstudio_vision_model", ph="модель, що бачить зображення"))
        gm.addWidget(self.label("Не обов'язково: модель LM Studio, що розуміє зображення (для скріншотів). Порожньо — основна."))
        g.addWidget(self.g_lms)
        l.addWidget(self.g_loc)
        l = self.card("Характер")
        self.emo_kind = Segmented([T("Стримана"), T("Жива"), T("Ярка")], {"restrained": 0, "lively": 1, "bright": 2}.get(c.get("emotionality", "lively"), 1))
        self.emo_kind.changed.connect(lambda i: self.app.set_character(["restrained", "lively", "bright"][i])); l.addWidget(self.emo_kind)
        l.addWidget(self.switch("Сарказм: легкі підколи", "sarcasm"))
        l.addWidget(self.switch("Може обиджатися на грубість", "hurt"))
        l.addWidget(self.field("Як тебе звати", "user_name"))
        l = self.card("Поведінка")
        l.addWidget(self.switch("Бачити екран (потрібна vision-модель)", "vision")); l.addWidget(self.switch("Питати дозволу на небезпечні дії", "confirm_dangerous"))
        l.addWidget(self.switch("Може писати першою", "proactive", self.app.reset_pro)); l.addWidget(self.switch("Звук повідомлень (коли згорнута)", "sound"))
        r = QHBoxLayout(); r.addWidget(self.label("Пише першою раз на, хв:"), 1); r.addWidget(self.edit("proactive_min", num=True, width=60)); r.addWidget(self.label("–")); r.addWidget(self.edit("proactive_max", num=True, width=60)); l.addLayout(r)
        l.addWidget(self.path_field("Папка з ярликами (ігри, програми)", "shortcuts_dir", "C:\\Users\\…\\games", folder=True))
        l = self.card("Команди, які можна без питань"); l.addWidget(self.label("Одна команда на рядок. * — будь-що. Команди з ; & | > завжди питають."))
        self.cmds = QPlainTextEdit("\r\n".join(c.get("allowed_cmds", []))); self.cmds.setPlaceholderText("ipconfig\r\ngit status\r\ndir *\r\nping *"); self.cmds.setFixedHeight(110); self.cmds.setMouseTracking(True); l.addWidget(self.cmds)
        l = self.card("Вигляд"); self.lang = QComboBox(); self.lang.addItem("English", "en"); self.lang.addItem("Українська", "uk"); self.lang.addItem("Русский", "ru")
        self.lang.setCurrentIndex(max(0, self.lang.findData(c.get("language", "en")))); self.lang.currentIndexChanged.connect(lambda i: self.app.set_language(self.lang.itemData(i)) if i >= 0 else None)
        l.addWidget(self.row("Мова", self.lang))
        self.theme = Segmented([T("Темна"), T("Світла")], 0 if c["theme"] == "dark" else 1); self.theme.setFixedWidth(140); self.theme.changed.connect(lambda i: self.app.set_theme_name("dark" if i == 0 else "light"))
        l.addWidget(self.row("Тема", self.theme)); self.emo = Segmented(["Apple", "Twemoji"], 0 if c["emoji_set"] == "apple" else 1); self.emo.setFixedWidth(140); self.emo.changed.connect(lambda i: self.app.set_emoji_set("apple" if i == 0 else "twemoji"))
        l.addWidget(self.row("Емодзі", self.emo))
        l = self.card("Вигляд"); l.addWidget(self.field("Шрифт (з папки поруч зі скриптом, після перезапуску)", "font", ph="Nunito"))
        orb_row = QWidget(); ol = QHBoxLayout(orb_row); ol.setContentsMargins(0, 0, 0, 0); ol.setSpacing(8)
        ol.addWidget(self.label("Розмір кружечка"), 1)
        self.orb_slider = QSlider(Qt.Orientation.Horizontal); self.orb_slider.setRange(60, 160); self.orb_slider.setValue(int(clamp(self.app.cfg.get("orb_size", 84), 60, 160))); self.orb_slider.setFixedWidth(110)
        self.orb_val = QLabel(f"{self.orb_slider.value()} px"); self.orb_val.setObjectName("clab")
        self.orb_slider.valueChanged.connect(self._orb_changed)
        ol.addWidget(self.orb_slider); ol.addWidget(self.orb_val); l.addWidget(orb_row)
        self.orb_preview = OrbPreview(self.app); self.orb_preview.setFixedHeight(150); l.addWidget(self.orb_preview)
        self.done = QPushButton("Готово"); self.done.setObjectName("done"); self.done.setCursor(Qt.CursorShape.PointingHandCursor); self.done.clicked.connect(self.app.close_settings); self.v.addWidget(self.done); self.v.addStretch(1)
        self.update_groups()
    def fill_service_ui(self):
        """Підганяє блок сервісу під обраний: чіп, підписи, ключ, база, список моделей із кешу."""
        c = self.app.cfg; svc = c.get("cloud_provider", "openrouter"); S = CLOUD_SERVICES[svc]
        for k, b in self.svc_btns.items(): b.setChecked(k == svc)   # обраний сервіс підсвічений
        self.key_label.setText(T("API-ключ") + " · " + S["title"])
        self.key_edit.setPlaceholderText(S["key_ph"]); self.key_edit.setText(svc_key(c, svc))
        self.base_box.setVisible(bool(S.get("base_edit")))
        if S.get("base_edit"):
            self.base_label.setText(T("Адреса сервісу (base URL)"))
            self.base_edit.setPlaceholderText("https://…/v1"); self.base_edit.setText(str((c.get("api_bases") or {}).get(svc) or S.get("base", "")))
        self.model_label.setText(T("Модель"))
        self.model_combo.blockSignals(True); self.model_combo.clear()
        cached = (c.get("api_models_cache") or {}).get(svc) or []
        items = cached if cached else ([svc_model(c, svc)] if svc_model(c, svc) else [])
        self.model_combo.addItems(items)
        self.model_combo.setCurrentText(svc_model(c, svc))
        self.model_combo.blockSignals(False)
        self.model_hint.setText(T("моделей у списку: {n}").replace("{n}", str(len(cached))) if cached else
                                T("Натисни ⟳ — підвантажу моделі з сервісу (потрібен ключ)"))
        # моделі оновлюються самостійно: є ключ і порожній кеш — тягнемо список без нагадування
        if svc_key(c, svc) and not cached and not (getattr(self, "_fetcher", None) and self._fetcher.isRunning())                 and time.time() - getattr(self, "_auto_at", 0) > 2:
            self._auto_at = time.time(); QTimer.singleShot(120, self.refresh_models)
    def commit_key(self):
        svc = self.app.cfg.get("cloud_provider", "openrouter")
        self.app.cfg.setdefault("api_keys", {})[svc] = self.key_edit.text().strip(); jsave(CFG_P, self.app.cfg)
        if svc == "google": self.app.cfg["google_api_key"] = self.key_edit.text().strip()      # сумісність зі старим полем
        if svc == "openrouter": self.app.cfg["openrouter_key"] = self.key_edit.text().strip()
        self.app.refresh_provider_ui()
    def commit_base(self):
        svc = self.app.cfg.get("cloud_provider", "openrouter")
        self.app.cfg.setdefault("api_bases", {})[svc] = self.base_edit.text().strip(); jsave(CFG_P, self.app.cfg)
    def commit_model(self, *a):
        svc = self.app.cfg.get("cloud_provider", "openrouter")
        txt = self.model_combo.currentText().strip()
        if txt: self.app.cfg.setdefault("api_models", {})[svc] = txt; jsave(CFG_P, self.app.cfg)
        if svc == "google": self.app.cfg["google_model"] = txt
        if svc == "openrouter": self.app.cfg["openrouter_model"] = txt
    def refresh_models(self):
        """Тягне список моделей сервісу у фоні й наповнює комбобокс (пошук — просто почни друкувати)."""
        svc = self.app.cfg.get("cloud_provider", "openrouter")
        self.key_edit.setText(self.key_edit.text().strip())   # спершу зберігаємо ключ, що ввірхений руками
        self.commit_key()
        self.model_hint.setText(T("Завантажую список моделей…")); self.model_btn.setEnabled(False)
        self._auto_at = time.time()
        self._fetcher = ModelFetcher(self.app.cfg, svc)
        self._fetcher.done.connect(self.on_models_fetched); self._fetcher.start()
    def on_models_fetched(self, svc, ids, err):
        self.model_btn.setEnabled(True)
        if err:
            self.model_hint.setText(T("Не вдалося отримати список") + ": " + err[:160]); return
        cur = svc_model(self.app.cfg, svc)
        self.model_combo.blockSignals(True); self.model_combo.clear()
        if ids: self.model_combo.addItems(ids)
        if cur: self.model_combo.setCurrentText(cur)
        self.model_combo.blockSignals(False)
        self.app.cfg.setdefault("api_models_cache", {})[svc] = ids[:400]; jsave(CFG_P, self.app.cfg)
        self.model_hint.setText(T("моделей у списку: {n}").replace("{n}", str(len(ids))))
    def update_groups(self):
        c = self.app.cfg; provider = c.get("provider", "cloud"); cloud = provider == "cloud"; loc = provider == "local"
        self.g_cloud.setVisible(cloud)
        self.g_loc.setVisible(loc); self.g_llama.setVisible(c["local_backend"] == "llamacpp"); self.g_lms.setVisible(c["local_backend"] != "llamacpp")
    def sync(self):
        c = self.app.cfg
        self.prov.set_index(0 if c.get("provider", "cloud") == "cloud" else 1)
        self.backend.set_index(0 if c["local_backend"] == "llamacpp" else 1)
        self.fill_service_ui()
        self.theme.set_index(0 if c["theme"] == "dark" else 1); self.lang.setCurrentIndex(max(0, self.lang.findData(c.get("language", "en")))); self.update_groups()
        if hasattr(self, "emo_kind"): self.emo_kind.set_index({"restrained": 0, "lively": 1, "bright": 2}.get(c.get("emotionality", "lively"), 1))
        if hasattr(self, "orb_slider"): self.orb_slider.setValue(int(clamp(c.get("orb_size", 84), 60, 160)))
    def _orb_changed(self, v):
        self.orb_val.setText(f"{v} px"); self.app.set_orb_size(v); self.orb_preview.update()
    def retranslate(self):
        for w in self.findChildren(QLabel):
            if hasattr(w, "raw_text"): w.setText(T(w.raw_text))
        for w in self.findChildren(QLineEdit):
            if hasattr(w, "raw_placeholder"): w.setPlaceholderText(T(w.raw_placeholder))
        self.prov.items = [T("API-хмара"), T("Локальна")]; self.theme.items = [T("Темна"), T("Світла")]
        self.prov.update(); self.theme.update(); self.fill_service_ui(); self.update()
        self.done.setText(T("Готово"))
    def commit(self):
        for key, le, num in self.edits: self.commit_one(key, le, num)
        self.app.cfg["allowed_cmds"] = [x.strip() for x in self.cmds.toPlainText().splitlines() if x.strip()]; jsave(CFG_P, self.app.cfg)
    def restyle(self):
        self.setStyleSheet(f"""QScrollArea{{background:transparent;border:none}}#inner{{background:transparent}}
#card{{background:{rgba(TH['bub'])};border-radius:16px}}#ctitle{{color:{TH['acc']}}}#clab{{color:{TH['fg2']}}}QLabel{{background:transparent}}
QLineEdit,QPlainTextEdit,QComboBox,QSpinBox{{background:{rgba(TH['inp'])};color:{TH['fg']};border:1px solid {rgba(TH['inpb'])};border-radius:11px;padding:6px 10px;selection-background-color:{TH['acc']}}}
QComboBox QAbstractItemView{{background:{TH['bg0']};color:{TH['fg']};selection-background-color:{TH['acc']}}}
QLineEdit:focus,QPlainTextEdit:focus{{border:1px solid {TH['acc']}}}
QSlider::groove:horizontal{{height:5px;background:{rgba(TH['inpb'])};border-radius:2px}}QSlider::handle:horizontal{{width:14px;margin:-5px 0;border-radius:7px;background:{TH['acc']}}}
QPushButton#browse{{background:{rgba(TH['btn'])};color:{TH['fg']};border:none;border-radius:11px}}QPushButton#browse:hover{{background:{rgba(TH['btnh'])}}}
QPushButton#done{{background:{TH['acc']};color:#fff;border:none;border-radius:17px;padding:10px}}""")
        for w in self.findChildren(QLabel): w.setFont(ufont(15, 700) if w.objectName() == "ctitle" else ufont(13, 500))
        for w in self.findChildren((QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QPushButton)): w.setFont(ufont(13, 500))
        self.update()

FONT_EXT = (".ttf", ".otf")
def font_files(mime):
    """Локальні файли шрифтів із перетягування."""
    if not mime.hasUrls(): return []
    return [Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in FONT_EXT]

class DropHint(QWidget):
    """Підказка поверх усього вікна, поки над ним тримають файл шрифту."""
    def __init__(self, parent):
        super().__init__(parent); self.text = "Відпусти файл шрифту тут"; self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.hide()
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r = QRectF(self.rect()).adjusted(5, 5, -5, -5)
        p.setPen(QPen(QColor(TH["acc"]), 2.2, Qt.PenStyle.DashLine)); p.setBrush(QColor(0, 0, 0, 120)); p.drawRoundedRect(r, 22, 22)
        p.setPen(QColor("#ffffff")); p.setFont(ufont(15, 700)); p.drawText(r.adjusted(14, 0, -14, 0), int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap), T(self.text))

class ThemeSnapshot(QWidget):
    """Короткий кроссфейд старого вигляду поверх уже застосованої теми."""
    def __init__(self, parent):
        super().__init__(parent); self.pixmap = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.effect = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity", self); self.animation.setDuration(260)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic); self.animation.finished.connect(self.hide)
    def fade_from(self, pixmap):
        self.animation.stop(); self.pixmap = pixmap; self.setGeometry(self.parentWidget().rect())
        self.effect.setOpacity(1.0); self.show(); self.raise_(); self.update()
        self.animation.setStartValue(1.0); self.animation.setEndValue(0.0); self.animation.start()
    def paintEvent(self, _):
        if not self.pixmap.isNull(): QPainter(self).drawPixmap(self.rect(), self.pixmap)

class OrbPreview(QWidget):
    """Живий перегляд кружечка: тягнеш слайдер — бачиш, яким він буде."""
    def __init__(self, app):
        super().__init__(app); self.app = app; self.face = Face(); self.setMinimumHeight(150)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = clamp(self.app.ow, 60, 160) * (self.height() - 14) / 160
        c = QPointF(self.width() / 2, self.height() / 2)
        path = QPainterPath(); path.addEllipse(c, d / 2, d / 2)
        lg = QLinearGradient(0, c.y() - d / 2, 0, c.y() + d / 2)
        lg.setColorAt(0, QColor(*TH["bg0"])); lg.setColorAt(1, QColor(*TH["bg1"]))
        p.save(); p.setClipPath(path); p.fillPath(path, QBrush(lg))
        gc = self.app.glow_color(); g = QRadialGradient(c, d / 2); c1 = QColor(gc); c1.setAlpha(int(TH["glow"])); c0 = QColor(gc); c0.setAlpha(0)
        g.setColorAt(0, c1); g.setColorAt(1, c0); p.fillRect(self.rect(), QBrush(g)); p.restore()
        bc = QColor(*TH["border"]); bc.setAlpha(140); p.setPen(QPen(bc, 1.4)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(c, d / 2, d / 2)
        draw_face(p, c, d / 195, self.face, time.time())
        p.end()

class MemoryWeb(QDialog):
    """Павутина пам'яті (як у мобільній Лурі): Лура в центрі, факти й побажання — вузли навколо.
    Клік по вузлу показує повний текст; клік по хрестику закриває."""
    def __init__(self, app):
        super().__init__(app, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.app = app; self.setModal(False); self.setFixedSize(380, 330)
        self.sel_text = ""; self.nodes = []; self.close_r = QRectF(self.width() - 34, 8, 26, 26)
        self.setWindowFlag(Qt.WindowType.Tool)
    def mousePressEvent(self, e):
        pos = QPointF(e.position())
        if self.close_r.contains(pos): self.close(); return
        for r, txt in self.nodes:
            if r.contains(pos): self.sel_text = txt; self.update(); return
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(TH["dlgb"]), 1.4)); p.setBrush(QColor(TH["dlg"])); p.drawRoundedRect(r, 18, 18)
        p.setFont(ufont(14, 700)); p.setPen(QColor(TH["fg"]))
        facts = self.app.mem.get("facts", {}); prefs = self.app.mem.get("prefs", [])
        title = T("Пам'ять — павутина")
        p.drawText(QPointF(18, 28), title + " · " + str(len(facts) + len(prefs)))
        draw_icon(p, "close", QRectF(self.close_r).adjusted(6, 6, -6, -6), QColor(*TH["icon"]))
        cx, cy, R1, R2 = self.width() / 2, 158, 74, 116
        cats = []
        if facts: cats.append((T("Факти"), [f"{k}: {v}" for k, v in list(facts.items())[:14]]))
        if prefs: cats.append((T("Побажання"), [x.get("text", "") for x in prefs[:14]]))
        self.nodes = []; line_c = QColor(*TH["border"]); line_c.setAlpha(70)
        node_c = QColor(TH["acc"])
        for i, (label, items) in enumerate(cats):
            a = math.pi * 2 / max(1, len(cats)) * i - math.pi / 2
            x1, y1 = cx + math.cos(a) * R1, cy + math.sin(a) * R1
            p.setPen(QPen(line_c, 1.2)); p.drawLine(QPointF(cx, cy), QPointF(x1, y1))
            p.setBrush(node_c); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(x1, y1), 4.6, 4.6)
            p.setPen(QColor(TH["fg2"])); p.setFont(ufont(10, 600))
            p.drawText(QPointF(x1 - 34, y1 - 9), QFontMetrics(ufont(10, 600)).elidedText(label, Qt.TextElideMode.ElideRight, 68))
            for j, txt in enumerate(items):
                aa = a + (j - (len(items) - 1) / 2) * .30
                x2, y2 = cx + math.cos(aa) * R2, cy + math.sin(aa) * R2
                p.setPen(QPen(line_c, 1)); p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                p.setBrush(node_c); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(x2, y2), 3.6, 3.6)
                self.nodes.append((QRectF(x2 - 9, y2 - 9, 18, 18), txt))
        p.setBrush(node_c); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(cx, cy), 8, 8)
        p.setPen(QColor(TH["fg"])); p.setFont(ufont(10, 700)); p.drawText(QPointF(cx - 14, cy + 22), "Лура")
        p.setPen(QColor(TH["fg2"])); p.setFont(ufont(11))
        info = self.sel_text or T("клікни по вузлику, щоб прочитати спогад")
        p.drawText(QRectF(18, self.height() - 58, self.width() - 36, 48), int(Qt.AlignmentFlag.AlignTop) | int(Qt.TextFlag.TextWordWrap),
                   QFontMetrics(ufont(11)).elidedText(info, Qt.TextElideMode.ElideRight, 2600))
        p.end()

MONTHS = {"uk": ["Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень", "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"],
          "ru": ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
WEEKDAYS = {"uk": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
            "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "en": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]}

class MenuPanel(QWidget):
    """Колонка меню всередині вікна Лури: календар із нагадуваннями (клік по дню — список, × — прибрати)
    і керування чатами (новий / відкрити / видалити). Вікно розширюється — панель «виповзає» зліва."""
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        today = dt.date.today()
        self.year, self.month, self.sel = today.year, today.month, today
        self.hits = []      # [(QRectF, kind, val)]

    def day_rems(self, d):
        with self.app.lock:
            return sorted([r for r in self.app.rem if dt.datetime.fromtimestamp(r["due"]).date() == d], key=lambda r: r["due"])
    def month_marked(self):
        days = set()
        with self.app.lock:
            for r in self.app.rem:
                dd = dt.datetime.fromtimestamp(r["due"]).date()
                if dd.year == self.year and dd.month == self.month: days.add(dd.day)
        return days
    def shift_month(self, k):
        m, y = self.month + k, self.year
        if m < 1: m, y = 12, y - 1
        if m > 12: m, y = 1, y + 1
        self.year, self.month = y, m; self.update()

    def mousePressEvent(self, e):
        p = QPointF(e.position())
        for rect, kind, val in self.hits:
            if not rect.contains(p): continue
            if kind == "close": self.app.close_menu_panel(); return   # ховаємо разом із звуженням вікна, не самі
            if kind == "prev": self.shift_month(-1); return
            if kind == "next": self.shift_month(1); return
            if kind == "day": self.sel = val; self.update(); return
            if kind == "delrem":
                with self.app.lock:
                    self.app.rem[:] = [r for r in self.app.rem if r["id"] != val]; jsave(REM_P, self.app.rem)
                self.update(); return
            if kind == "newchat": self.app.new_chat(); self.update(); return
            if kind == "chat": self.app.load_chat(val); self.update(); return
            if kind == "delchat": self.app.remove_chat(val); self.update(); return

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(TH["dlgb"]), 1.2)); p.setBrush(QColor(rgba(TH["bub"])))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 18, 18)
        self.hits = []
        # × у кружечку, хіт-бокс 30×30 — влучати легше
        close_r = QRectF(self.width() - 38, 6, 30, 30); self.hits.append((close_r, "close", None))
        p.setFont(ufont(14, 700)); p.setPen(QColor(TH["fg"])); p.drawText(QPointF(18, 28), T("Меню"))
        p.setPen(QPen(QColor(TH["fg2"]), 1.2)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(close_r)
        draw_icon(p, "close", close_r.adjusted(9, 9, -9, -9), QColor(*TH["icon"]))
        # ── календар
        y0 = 44
        prev_r, next_r = QRectF(14, y0, 30, 26), QRectF(self.width() - 44, y0, 30, 26)
        self.hits.append((prev_r, "prev", None)); self.hits.append((next_r, "next", None))
        p.setFont(ufont(13, 700)); p.setPen(QColor(TH["acc"]))
        p.drawText(prev_r, Qt.AlignmentFlag.AlignCenter, "‹"); p.drawText(next_r, Qt.AlignmentFlag.AlignCenter, "›")
        p.setPen(QColor(TH["fg"]))
        p.drawText(QPointF(self.width() / 2 - 56, y0 + 18), f"{MONTHS.get(LANG, MONTHS['uk'])[self.month - 1]} {self.year}")
        colw = (self.width() - 28) / 7
        p.setFont(ufont(9, 600)); p.setPen(QColor(TH["fg2"]))
        for i, wd in enumerate(WEEKDAYS.get(LANG, WEEKDAYS["uk"])): p.drawText(QPointF(14 + i * colw + colw / 2 - 9, y0 + 36), wd)
        first = dt.date(self.year, self.month, 1).weekday()
        ndays = (dt.date(self.year + (self.month == 12), self.month % 12 + 1, 1) - dt.timedelta(days=1)).day
        marked, today, gy = self.month_marked(), dt.date.today(), y0 + 44
        for i in range(42):
            day = i - first + 1
            if day < 1 or day > ndays: continue
            cell = QRectF(14 + (i % 7) * colw, gy + (i // 7) * 24, colw, 24)
            d = dt.date(self.year, self.month, day)
            sel, tod = d == self.sel, d == today
            if sel:
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(TH["acc"])); p.drawRoundedRect(cell.adjusted(2, 2, -2, -2), 8, 8)
            p.setFont(ufont(11, 700 if (sel or tod) else 500))
            p.setPen(QColor("#ffffff") if sel else QColor(TH["acc"] if tod else TH["fg"]))
            p.drawText(cell, Qt.AlignmentFlag.AlignCenter, str(day))
            if day in marked and not sel:
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(TH["acc"])); p.drawEllipse(QPointF(cell.center().x(), cell.bottom() - 3), 2, 2)
            self.hits.append((cell, "day", d))
        # ── нагадування вибраного дня
        ry = gy + 6 * 24 + 12
        p.setFont(ufont(12, 700)); p.setPen(QColor(TH["acc"]))
        p.drawText(QPointF(18, ry), T("Нагадування") + " · " + self.sel.strftime("%d.%m"))
        ry += 6
        rems = self.day_rems(self.sel)
        if not rems:
            p.setFont(ufont(11, 500)); p.setPen(QColor(TH["fg2"])); p.drawText(QPointF(18, ry + 16), T("— немає —"))
        for i, rem in enumerate(rems[:5]):
            rowy = ry + i * 22
            p.setFont(ufont(11, 500)); p.setPen(QColor(TH["fg"]))
            p.drawText(QPointF(18, rowy + 16), dt.datetime.fromtimestamp(rem["due"]).strftime("%H:%M") + "  " + rem["text"][:32])
            xr = QRectF(self.width() - 38, rowy - 2, 26, 26); self.hits.append((xr, "delrem", rem["id"]))   # × 26×26 у кружечку
            p.setPen(QPen(QColor(TH["fg2"]), 1.1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(xr.adjusted(0, 1, 0, -1))
            draw_icon(p, "close", xr.adjusted(8, 8, -8, -8), QColor(*TH["icon"]))
        # ── чати
        cy = ry + 122
        p.setFont(ufont(12, 700)); p.setPen(QColor(TH["acc"])); p.drawText(QPointF(18, cy), T("Чати"))
        newr = QRectF(self.width() - 120, cy - 16, 102, 22); self.hits.append((newr, "newchat", None))
        p.setPen(QPen(QColor(TH["acc"]), 1.2)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRoundedRect(newr, 11, 11)
        p.setFont(ufont(10, 700)); p.drawText(newr, Qt.AlignmentFlag.AlignCenter, "+ " + T("Новий чат"))
        rows = max(3, int((self.height() - cy - 14) / 24))
        for i, s in enumerate(list(self.app.sessions)[:rows]):
            rowy = cy + 12 + i * 24
            active = s["id"] == self.app._chat_id()
            p.setFont(ufont(11, 700 if active else 500)); p.setPen(QColor(TH["fg"] if active else TH["fg2"]))
            p.drawText(QPointF(18, rowy + 16), ("• " if active else "") + (s.get("title") or T("Новий чат"))[:40])
            xr = QRectF(self.width() - 38, rowy - 1, 26, 26); self.hits.append((xr, "delchat", s["id"]))   # × 26×26 у кружечку
            p.setPen(QPen(QColor(TH["fg2"]), 1.1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(xr.adjusted(0, 1, 0, -1))
            draw_icon(p, "close", xr.adjusted(8, 8, -8, -8), QColor(*TH["icon"]))
            self.hits.append((QRectF(14, rowy, self.width() - 80, 22), "chat", s["id"]))
        p.end()

def fmt_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB": return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
def dropped_files(mime):
    if not mime.hasUrls(): return []
    out = []
    for u in mime.urls():
        if u.isLocalFile() and Path(u.toLocalFile()).is_file(): out.append(Path(u.toLocalFile()))
    return out

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
def read_file_content(p, max_chars=15000):
    """Текстовий вміст файлу майже будь-якого типу: txt/код/csv/лог — як є, PDF і DOCX — розпаковано.
    Бінарники (exe, zip, медіа) → None — їх лишаємо карткою-тегом."""
    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)[:max_chars]
        if ext == ".docx":
            import docx
            return "\n".join(x.text for x in docx.Document(str(p)).paragraphs)[:max_chars]
        data = p.read_bytes()
        if b"\0" in data[:4096]: return None
        return data.decode("utf-8", errors="replace")[:max_chars]
    except Exception:
        return None

def read_image_data_url(p, max_w=1600):
    """Картинку будь-якого формату → data:image/jpeg (у зір моделі)."""
    try:
        img = QImage(str(p))
        if img.isNull(): return None
        if img.width() > max_w: img = img.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
        buf = QBuffer(); buf.open(QIODevice.OpenModeFlag.WriteOnly); img.save(buf, "JPEG", 85)
        return "data:image/jpeg;base64," + base64.b64encode(bytes(buf.data())).decode()
    except Exception:
        return None

class Bubble(QLabel):
    """Бульбашка; фон користувача малюється тут, тож колір панелі змінюється без перестилізації."""
    def __init__(self, role):
        super().__init__(); self.role = role; self.big = False
    def paintEvent(self, e):
        if self.role == "user" and not self.big:
            p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(TH["ubub"])); p.drawRoundedRect(QRectF(self.rect()), 17, 17); p.end()
        super().paintEvent(e)

class FileCard(QWidget):
    """Прикріплений файл у чаті: просто картка (назва, тип, розмір). Вміст у текст не перетворюється."""
    def __init__(self, path):
        super().__init__(); self.path = Path(path); self.setFixedHeight(58); self.setMinimumWidth(190); self.setMaximumWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setToolTip(str(self.path))
        try: self.size_txt = fmt_size(self.path.stat().st_size)
        except OSError: self.size_txt = "—"
        self.ext = self.path.suffix.lstrip(".").upper()[:5] or "FILE"
    def sizeHint(self): return QSize(240, 58)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r = QRectF(self.rect()); fg = QColor(TH["ufg"])
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(TH["ubub"])); p.drawRoundedRect(r, 17, 17)
        ir = QRectF(10, 10, 38, 38); p.setBrush(QColor(255, 255, 255, 46)); p.drawRoundedRect(ir, 11, 11)
        draw_icon(p, "file", QRectF(ir.x() + 10, ir.y() + 1, 18, 20), fg)
        p.setPen(fg); p.setFont(ufont(9, 800)); p.drawText(QRectF(ir.x(), ir.y() + 25, 38, 11), Qt.AlignmentFlag.AlignCenter, self.ext)
        f = ufont(13, 700); fm = QFontMetrics(f); p.setFont(f)
        p.drawText(QRectF(58, 9, r.width() - 70, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(self.path.name, Qt.TextElideMode.ElideMiddle, int(r.width() - 70)))
        fg.setAlpha(190); p.setPen(fg); p.setFont(ufont(11, 500)); p.drawText(QRectF(58, 29, r.width() - 70, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.size_txt)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            try: launch(str(self.path))
            except Exception: pass

class AttachBar(QWidget):
    """Рядок чипів із файлами, які щойно прикріпили (над полем вводу)."""
    removed = pyqtSignal(int)
    def __init__(self):
        super().__init__(); self.files = []; self.hit = []; self.setFixedHeight(0); self.hide()
    def set_files(self, files):
        self.files = list(files); self.setFixedHeight(34 if self.files else 0); self.setVisible(bool(self.files)); self.update()
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); f = ufont(12, 600); p.setFont(f); fm = QFontMetrics(f); x = 0.0; self.hit = []
        for i, fp in enumerate(self.files):
            name = fm.elidedText(fp.name, Qt.TextElideMode.ElideMiddle, 130); w = 36 + fm.horizontalAdvance(name) + 30
            if x + w > self.width() and i > 0:
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(*TH["btn"])); p.drawRoundedRect(QRectF(x, 2, 44, 30), 15, 15)
                p.setPen(QColor(TH["fg"])); p.drawText(QRectF(x, 2, 44, 30), Qt.AlignmentFlag.AlignCenter, f"+{len(self.files) - i}"); break
            rect = QRectF(x, 2, w, 30); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(*TH["btn"])); p.drawRoundedRect(rect, 15, 15)
            draw_icon(p, "file", QRectF(x + 10, 7, 14, 18), QColor(*TH["icon"]))
            p.setPen(QColor(TH["fg"])); p.drawText(QRectF(x + 30, 2, w - 56, 30), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
            draw_icon(p, "close", QRectF(rect.right() - 24, 8, 16, 16), QColor(*TH["icon"])); self.hit.append((QRectF(rect.right() - 30, 2, 30, 30), i)); x += w + 6
    def mousePressEvent(self, e):
        for r, i in self.hit:
            if r.contains(QPointF(e.position())): self.removed.emit(i); return

class ResizeGrip(QWidget):
    """Прозорий трикутник у правому нижньому куті для зміни розміру вікна."""
    def __init__(self, win):
        super().__init__(win); self.win = win; self.hover = False; self.setFixedSize(GRIP, GRIP)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor); self.setMouseTracking(True)
    def enterEvent(self, e): self.hover = True; self.update()
    def leaveEvent(self, e): self.hover = False; self.update()
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); c = QColor(*TH["line"]); c.setAlpha(120 if (self.hover or self.win.resizing) else 48)
        s = GRIP; path = QPainterPath(); path.moveTo(s - 8, s - 30); path.lineTo(s - 8, s - 8); path.lineTo(s - 30, s - 8); path.closeSubpath()
        p.setPen(QPen(c, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)); p.setBrush(c); p.drawPath(path)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.win.begin_resize("rb", e.globalPosition().toPoint())
    def mouseMoveEvent(self, e):
        if self.win.resizing: self.win.resize_move(e.globalPosition().toPoint())
    def mouseReleaseEvent(self, e): self.win.end_resize()

class Lura(QWidget):
    def __init__(self, bridge):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setMouseTracking(True); self.setAcceptDrops(True)
        self._morph = 0.0; self._sp = 0.0; self.mode = "chat"; self.busy = False; self.unread = False; self.settings_open = False; self.menu_open = False
        self.bridge = bridge; self.cfg = load_cfg(); self.lock = threading.RLock(); self.sticky = ""
        self.cw, self.ch = int(clamp(self.cfg["chat_w"], 290, 760)), int(clamp(self.cfg["chat_h"], 300, 1100))
        self.ow = int(clamp(self.cfg.get("orb_size", ORB_SIZE), 60, 160))     # розмір кружечка — з налаштувань
        self.resizing = False; self._rs = None; self._rs_pending = None; self._rs_last = 0.0; self._was_bottom = True
        self.attachments = []; self.cards = []; self.pc = [float(v) for v in self.cfg["face_rgb"]]; self.pa = None; self._inp_t = 0.0; self._pal_reset_at = 0.0
        self.hc = 1.0 if self.target_compact() else 0.0
        self.mem = jload(MEM_P, {}); self.mem.setdefault("facts", {}); self.mem.setdefault("prefs", [])
        self.rem = jload(REM_P, [])
        # чати-сесії, як у мобільній версії: список чатів + поточний; стара історія мігрує в «Старий чат»
        self.sessions = jload(CHATS_P, [])
        if not isinstance(self.sessions, list): self.sessions = []
        old_hist = jload(HIST_P, [])
        if not self.sessions and old_hist:
            self.sessions = [{"id": self._new_chat_id(), "title": "Старий чат", "created": time.time(), "messages": old_hist[-80:]}]
        if not self.sessions: self.sessions = [{"id": self._new_chat_id(), "title": "Новий чат", "created": time.time(), "messages": []}]
        if str(self.cfg.get("chat_id", "")) not in [s["id"] for s in self.sessions]: self.cfg["chat_id"] = self.sessions[0]["id"]
        self.history = list(self.current_session().get("messages", []))
        Path(self.cfg["shortcuts_dir"]).mkdir(parents=True, exist_ok=True)
        self.face = Face(); self.tools = Tools(self); self.toast = Toast(); self.toast.clicked.connect(self.expand)
        self.server = LocalServer(self); self.server.msg.connect(self.set_sticky)
        self.last_touch = time.time(); self._last = time.time(); self._press = None; self._rs = None; self._fallback = None; self.talk_until = 0.0
        self.miss_level = 0; self.typing_row = None; self.bubbles = []; self.worker = None; self.stream = self.new_stream()
        self._user_emotion = None; self._user_emotion_until = 0.0; self._last_pet = 0.0; self._pet = None
        self._user_touched = False   # чи встиг користувач написати першим (тоді стартове привітання не треба)
        ag = QGuiApplication.primaryScreen().availableGeometry()
        self.chat_rect = QRect(ag.right() - self.cw - 24, ag.bottom() - self.ch - 24, self.cw, self.ch)
        a = self.anchor(self.cw); self.orb_rect = QRect(int(self.chat_rect.x() + a.x() - self.ow / 2), int(self.chat_rect.y() + a.y() - self.ow / 2), self.ow, self.ow)
        self.setGeometry(self.chat_rect)
        self.next_pro = time.time() + random.uniform(self.cfg["proactive_min"], self.cfg["proactive_max"]) * 60
        self.anim = QPropertyAnimation(self, b"morph", self); self.anim.setDuration(560)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic); self.anim.finished.connect(self._anim_done)
        self.sp_anim = QPropertyAnimation(self, b"sp", self); self.sp_anim.setDuration(380); self.sp_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.rs_timer = QTimer(self); self.rs_timer.setSingleShot(True); self.rs_timer.timeout.connect(self._rs_flush)
        self.ping = None
        if QSoundEffect is not None:
            try:
                if not PING_P.exists(): make_ping(PING_P)
                self.ping = QSoundEffect(self); self.ping.setSource(QUrl.fromLocalFile(str(PING_P))); self.ping.setVolume(.7)
            except Exception: self.ping = None
        self.openlura_server, self.openlura_url = start_openlura_assets() if QWebEngineView is not None else (None, "")
        self.face_view = None; self.face_view_ready = False; self._face_view_size = (max(1, self.cw-16), 112)
        self._web_compact = None; self._web_scale = 1.0
        self._queued_face_emotion = ("happy", .8, 0); self._queued_face_mode = ("think", False)
        self.build_ui(); self.build_tray(); self.apply_theme(); self.drop_hint = DropHint(self); self.disable_child_drops()
        if EMO_SIG is not None: EMO_SIG.ready.connect(self.rerender_soon)
        self.re_t = QTimer(self); self.re_t.setSingleShot(True); self.re_t.timeout.connect(self.rerender)
        self.t_anim = QTimer(self); self.t_anim.timeout.connect(self.tick); self.t_anim.start(25)
        self.t_slow = QTimer(self); self.t_slow.timeout.connect(self.slow); self.t_slow.start(1000)
        self.render_history()
        if self.cfg["provider"] == "local": QTimer.singleShot(800, self.server.ensure)
        if self.configured():
            QTimer.singleShot(2500, self.maybe_startup_greeting)
        else:
            greeting = startup_greeting()
            info = T("Привіт! Я Лура. Мордашка реагує на твої слова й без моделі. Щоб я могла відповідати текстом, під'єднай OpenRouter, Google Gemini з файлом keys.txt або локальну модель.")
            self.add_bubble(greeting + " " + info, "lura")

    # ── геометрія шапки: велике обличчя ↔ «віконечко» (компактний режим)
    def maybe_startup_greeting(self):
        """Привітання при запуску — без дублів: якщо користувач уже написав першим або чат уже
        починається з привітання Лури, окреме привітання не потрібне. Нотатка — мовою з налаштувань."""
        if self._user_touched or self.busy: return
        h = self.history
        if h and h[-1]["role"] == "assistant" and not any(m["role"] == "user" for m in h[-4:]): return
        style = random.choice(P("greeting_styles") or ["коротке й миле"])
        note = P("note_greeting").replace("{style}", style)
        self.system_turn(note, fallback=f"[[happy]] {startup_greeting(LANG)}")
    def target_compact(self): return self.settings_open or self.cw < 340 or self.ch < 500
    def hdr_h(self): return lerp(164, 64, self.hc)
    def anchor(self, w):
        return QPointF(lerp(w / 2, 12 + 38 * self._sp + PW / 2, self.hc), lerp(FACE_CY, 10 + PH / 2 + 2, self.hc))
    def face_center_local(self):
        t, a, b = self._morph, self.chat_rect, self.orb_rect; an = self.anchor(a.width())
        fx = lerp(a.x() + an.x(), b.x() + b.width() / 2, t); fy = lerp(a.y() + an.y(), b.y() + b.height() / 2, t)
        return QPointF(fx - self.x(), fy - self.y())
    def face_scale(self):
        big = clamp(self.cw / 370, .78, 1.1) * .84
        return lerp(lerp(big, .34, self.hc), .46 * self.ow / 84, self._morph)

    # ── анімації: згортання в кружечок та перехід у налаштування
    def _get_morph(self): return self._morph
    def _set_morph(self, t):
        self._morph = t; a, b = self.chat_rect, self.orb_rect
        self.setGeometry(*[round(lerp(x, y, t)) for x, y in ((a.x(), b.x()), (a.y(), b.y()), (a.width(), b.width()), (a.height(), b.height()))])
        if self.mode == "orb" and t > .5: self.body.hide()   # у кружечку текст чату не має обрізатись по краях
        # Згортаємо вміст м'яко протягом усього руху, а не ховаємо його різко на першій половині.
        self.layout_face_view(); self.update()
    morph = pyqtProperty(float, _get_morph, _set_morph)
    def _get_sp(self): return self._sp
    def _set_sp(self, v): self._sp = v; self.layout_body(); self.update()
    sp = pyqtProperty(float, _get_sp, _set_sp)
    def animating(self): return self.anim.state() == QPropertyAnimation.State.Running
    def _anim_done(self):
        if self.mode == "orb": self.body.hide()
        else: self.layout_body(); self.inp.setFocus(); self.scroll_bottom()
    def collapse(self):
        if self.menu_open: self.close_menu_panel(); return
        if self.mode != "chat" or self.animating() or self.resizing: return
        self.grip.hide()
        self.chat_rect = self.geometry(); an = self.anchor(self.chat_rect.width())
        cx, cy = self.chat_rect.x() + an.x(), self.chat_rect.y() + an.y()
        self.orb_rect = QRect(int(cx - self.ow / 2), int(cy - self.ow / 2), self.ow, self.ow); self.mode = "orb"
        self.sync_face_compact()      # CSS-перехід мордашки стартує разом із рухом вікна — одна анімація, без стрибка
        self.anim.setStartValue(0.0); self.anim.setEndValue(1.0); self.anim.start()
    def expand(self):
        if self.mode != "orb" or self.animating(): return
        self.orb_rect = self.geometry(); c = self.orb_rect.center(); an = self.anchor(self.cw)
        ag = (QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()).availableGeometry()
        x = int(clamp(c.x() - an.x(), ag.left() + 6, ag.right() - self.cw - 6)); y = int(clamp(c.y() - an.y(), ag.top() + 6, ag.bottom() - self.ch - 6))
        self.chat_rect = QRect(x, y, self.cw, self.ch); self.mode = "chat"; self.unread = False; self.toast.hide(); self.body.show()
        self.sync_face_compact()
        self.last_touch=time.time(); self.miss_level=0
        self.anim.setStartValue(1.0); self.anim.setEndValue(0.0); self.anim.start()
    def toggle(self): self.expand() if self.mode == "orb" else self.collapse()
    def set_orb_size(self, n):
        n = int(clamp(n, 60, 160))
        if n == self.ow: return
        self.ow = n; self.cfg["orb_size"] = n; jsave(CFG_P, self.cfg)
        if self.mode == "orb":      # кружечок уже на екрані — міняємо розмір одразу, разом із мордашкою
            c = self.geometry().center()
            self.orb_rect = QRect(int(c.x() - n / 2), int(c.y() - n / 2), n, n)
            self.setGeometry(self.orb_rect); self.layout_face_view()
        self.sync_face_compact()
    def open_settings(self):
        if self.menu_open: self.close_menu_panel(); return
        if self.mode == "orb": self.expand()
        self.settings_open = True; self.settings.sync(); self.sp_anim.stop(); self.sp_anim.setStartValue(self._sp); self.sp_anim.setEndValue(1.0); self.sp_anim.start()
        self.sync_face_compact()
    def close_settings(self):
        self.settings.commit(); self.settings_open = False; self.sp_anim.stop(); self.sp_anim.setStartValue(self._sp); self.sp_anim.setEndValue(0.0); self.sp_anim.start()
        self.refresh_provider_ui(); self.sync_face_compact()
    def toggle_settings(self): self.close_settings() if self.settings_open else self.open_settings()

    # ── побудова інтерфейсу
    def build_ui(self):
        self.body = QWidget(self); self.body.setMouseTracking(True)
        self.chat_page = ChatPage(self.body); self.chat_page.owner = self; self.chat_page.setMouseTracking(True)
        v = QVBoxLayout(self.chat_page); v.setContentsMargins(12, 4, 12, 12); v.setSpacing(8)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.scroll.setMouseTracking(True)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none}"); self.scroll.viewport().setAutoFillBackground(False)
        self.msgs = QWidget(); self.msgs.setObjectName("msgs"); self.msgs.setStyleSheet("#msgs{background:transparent}"); self.mv = QVBoxLayout(self.msgs)
        self.mv.setContentsMargins(4, 26, 4, 4); self.mv.setSpacing(6); self.mv.addStretch(1); self.scroll.setWidget(self.msgs)
        self.status = QLabel(); self.status.setFixedHeight(16)
        row = QHBoxLayout(); row.setSpacing(6)
        self.inp = Input(); self.inp.setPlaceholderText(T("Напиши мені…")); self.inp.setFixedHeight(44); self.inp.send.connect(self.on_send)
        self.inp.textChanged.connect(lambda: self.set_face_mode("listen", bool(self.inp.toPlainText().strip())))
        self.eye = IconButton("eye", checkable=True); self.eye.setToolTip("Показати Лурі екран разом із повідомленням")
        self.go = IconButton("send"); self.go.accent = True; self.go.clicked.connect(self.on_send)
        self.attach = IconButton("clip"); self.attach.setToolTip(T("Прикріпити файл")); self.attach.clicked.connect(self.pick_files)
        self.attach_bar = AttachBar(); self.attach_bar.removed.connect(self.remove_attachment)
        for b in (self.attach, self.eye, self.go): b.setFixedSize(40, 40)
        row.addWidget(self.inp, 1); row.addWidget(self.attach); row.addWidget(self.eye); row.addWidget(self.go)
        v.addWidget(self.scroll, 1); v.addWidget(self.status); v.addWidget(self.attach_bar); v.addLayout(row)
        self.chat_page.fade = Fade(self, self.chat_page); self.chat_page.fade.raise_()
        self.settings = SettingsPage(self, self.body)
        self.seg = Segmented([T("API-хмара"), T("Локальна")], 0 if self.cfg.get("provider", "cloud") == "cloud" else 1, 28); self.seg.setParent(self.body); self.seg.changed.connect(lambda i: self.set_provider("cloud" if i == 0 else "local"))
        self.b_back = IconButton("back", self.body); self.b_back.clicked.connect(self.close_settings); self.b_back.setToolTip("Назад до чату")
        self.b_close = IconButton("close", self.body); self.b_close.setToolTip("Вийти"); self.b_close.clicked.connect(self.quit_app)
        self.b_min = IconButton("min", self.body); self.b_min.setToolTip("Згорнути в кружечок"); self.b_min.clicked.connect(self.collapse)
        self.b_gear = IconButton("gear", self.body); self.b_gear.setToolTip("Налаштування"); self.b_gear.clicked.connect(self.toggle_settings)
        self.b_menu = IconButton("menu", self.body); self.b_menu.setToolTip("Меню — календар і чати"); self.b_menu.clicked.connect(self.toggle_menu_panel)
        self.b_theme = IconButton("sun", self.body); self.b_theme.setToolTip("Світла / темна тема"); self.b_theme.clicked.connect(self.toggle_theme)
        for b in (self.b_back, self.b_close, self.b_min, self.b_gear, self.b_menu, self.b_theme): b.setFixedSize(32, 32)
        if QWebEngineView is not None and self.openlura_url:
            self.face_view = QWebEngineView(self); self.face_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.face_view.setStyleSheet("background: transparent; border: none;")
            self.face_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
            self.face_view.loadFinished.connect(self.openlura_loaded); self.face_view.load(QUrl(self.openlura_url))
            self.face_view.show()
        self.theme_snapshot = ThemeSnapshot(self); self.theme_snapshot.hide()
        self.menu_panel = MenuPanel(self); self.menu_panel.hide()
        self.menu_anim = QPropertyAnimation(self, b"geometry", self); self.menu_anim.setDuration(320)
        self.menu_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.menu_anim.valueChanged.connect(lambda _: self.layout_body())
        self.menu_anim.finished.connect(self._menu_anim_done)
        self.grip = ResizeGrip(self)
        self.refresh_provider_ui(); self.layout_body()
    def layout_body(self):
        cw, ch, hc, sp = self.cw, self.ch, self.hc, self._sp
        mw = self.menu_w()                                 # колонка меню: вікно розширене вліво
        self.body.setGeometry(mw, 0, cw, ch); H = int(self.hdr_h()); py = H - 4; ph = max(60, ch - py)
        self.chat_page.setGeometry(int(-sp * cw), py, cw, ph); self.settings.setGeometry(int((1 - sp) * cw) + 8, py, cw - 16, ph)
        self.chat_page.setVisible(sp < .999); self.settings.setVisible(sp > .001)
        if mw > 0:      # панель меню стоїть на місці на екрані; віконний край «відкриває» її зліва
            self.menu_panel.setGeometry(mw - MENU_W, 0, MENU_W, ch)
            self.menu_panel.show(); self.menu_panel.raise_()
        elif self.menu_anim.state() != QPropertyAnimation.State.Running:
            self.menu_panel.hide()
        y = int(lerp(12, 18, hc))
        for b, off in ((self.b_close, 34), (self.b_min, 70), (self.b_gear, 106), (self.b_menu, 142), (self.b_theme, 178)): b.move(cw - 12 - off, y)
        self.b_theme.setVisible(hc < .5); self.b_gear.accent = sp > .5
        self.seg.setGeometry(12, 12, max(140, cw - 218), 28); self.seg.setVisible(hc < .5 and sp < .02)
        self.b_back.move(int(lerp(-34, 12, sp)), y); self.b_back.setVisible(sp > .02)
        self.layout_face_view()
        self.grip.setGeometry(cw + mw - GRIP, ch - GRIP, GRIP, GRIP); self.grip.setVisible(self.mode == "chat" and self._morph < .02 and not self.menu_open)
        if self.resizing: return            # під час перетягування важкі речі не чіпаємо
        if self.face_view:
            for b in (self.b_back, self.b_close, self.b_min, self.b_gear, self.b_menu, self.b_theme, self.seg): b.raise_()
        self.grip.raise_(); wmax = int(cw * .76)
        for lab in self.bubbles + self.cards: lab.setMaximumWidth(wmax)
    def layout_face_view(self):
        if not self.face_view: return
        center = self.face_center_local()
        # Розмір змінюємо лише у спокійному розгорнутому чаті; під час анімацій і перетягування — лише рухаємо.
        # Віконце робимо вищим за шапку, а контент масштабуємо до .9 — лице трохи менше й не обрізається, коли «стрибає».
        if not self.hc and not self.animating() and not self.resizing and self.mode == "chat":
            self._face_view_size = (max(1, self.cw - 16), max(1, int(self.hdr_h()) - 40))   # cw, не width(): з відкритим меню вікно ширше
        w, h = self._face_view_size
        self.face_view.setGeometry(round(center.x() - w / 2), round(center.y() - h / 2), w, h)
        self.face_view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.hc > .5 or self._morph > .001 or self.mode == "orb")
        self.face_view.setVisible(True)
    def openlura_loaded(self, ok):
        self.face_view_ready=bool(ok)
        if not ok: return
        self._web_compact = None
        self.sync_face_compact()
        self.apply_face_palette()
        self._apply_face_emotion(); self._apply_face_mode()
    def _apply_face_emotion(self):
        if not self.face_view or not self.face_view_ready:return
        name,intensity,duration=self._queued_face_emotion
        js=f"window.luraSetEmotion({json.dumps(name)},{float(intensity):.3f},{float(duration):.0f})"
        self.face_view.page().runJavaScript(js)
    def _apply_face_mode(self):
        if not self.face_view or not self.face_view_ready:return
        mode,on=self._queued_face_mode
        call="luraSetThinking" if mode=="think" else "luraSetListening"
        self.face_view.page().runJavaScript(f"window.{call}({str(bool(on)).lower()})")
    def sync_face_compact(self):
        if not self.face_view or not self.face_view_ready: return
        orb = self.mode == "orb"
        compact = orb or self.settings_open or self.cw < 340 or self.ch < 500
        # у кружечку мордашка більша й масштабується разом із розміром кружечка; у чаті — трохи менша, щоб стрибки не обрізались
        scale = clamp(.32 * self.ow / 84, .14, .8) if orb else (.26 if compact else .9)
        if compact == self._web_compact and abs(scale - self._web_scale) < .004: return
        self._web_compact = compact; self._web_scale = scale
        self.face_view.page().runJavaScript(
            f"window.luraSetCompact({str(compact).lower()},{str(orb).lower()});"
            f"var s=document.getElementById('stage');if(s)s.style.transform='scale({scale:.3f})'")
    def set_face_emotion(self,spec,hold=4):
        self.face.set(spec,hold)
        weights,_=parse_spec(spec)
        chosen=max(weights,key=weights.get) if weights else "neutral"
        raw=spec.split(":")[0].split(",")[0].strip().lower()      # перше слово специфікації...
        name=raw if raw in OPENLURA_EMOTIONS else OPENLURA_EMOTIONS.get(chosen,"calm")   # ...якщо рушій його знає (hurt, cozy, giggle)
        # Відкриті переходи OpenLura не мають різко обрізати попередній вираз.
        # hold=0 означає постійний базовий стан; інакше залишаємо реакцію на заданий час.
        self._queued_face_emotion=(name,.88,max(0,float(hold)*1000))
        self._apply_face_emotion()
        self.apply_face_palette(name)
        self._pal_reset_at = (time.time() + hold) if hold > 0 else 0.0   # після емоції колір повертається до основного рожевого
    def set_face_mode(self,mode,on):
        self._queued_face_mode=(mode,bool(on)); self._apply_face_mode()
    def refresh_provider_ui(self):
        provider = self.cfg.get("provider", "cloud")
        self.seg.set_index(0 if provider == "cloud" else 1)
        self.seg.items = [T("API-хмара"), T("Локальна")]; self.seg.update()
        backend = api_provider(self.cfg)
        self.seg.setToolTip("Локально: " + ("llama.cpp" if self.cfg["local_backend"] == "llamacpp" else "LM Studio") if provider == "local" else ("Google Gemini" if backend == "google" else "OpenRouter"))
        self.settings.sync()
    def apply_theme(self):
        set_theme(self.cfg["theme"]); self.apply_rgb_theme(); QApplication.instance().setStyleSheet(qss())
        self.apply_face_palette(to_base=True)      # тема завжди застосовується з основного рожевого, а не з відтінку минулої емоції
        self.b_theme.icon_name = "sun" if self.cfg["theme"] == "dark" else "moon"
        self.style_input()
        self.inp.setFont(ufont(14)); self.status.setFont(ufont(12)); self.status.setStyleSheet(f"color:{TH['fg2']}")
        self.toast.restyle(); self.settings.restyle()
        for lab in self.bubbles: self.style_bubble(lab)
        self.set_status(""); self.update()
        for w in self.body.findChildren(IconButton): w.update()
    def style_input(self):
        self.inp.setStyleSheet(f"QPlainTextEdit{{background:{rgba(TH['inp'])};color:{TH['fg']};border:1px solid {rgba(TH['inpb'])};border-radius:18px;padding:7px 13px}}")
    def apply_rgb_theme(self):
        rgb = [int(clamp(round(v), 0, 255)) for v in self.pc]      # поточний колір панелі (залежить від емоції)
        color = QColor(*rgb); accent = color.name(); TH["acc"] = accent; TH["ubub"] = accent
        TH["border"] = tuple(rgb); TH["hatch"] = tuple(rgb); TH["dlgb"] = accent
        TH["inpb"] = (*rgb, 145); TH["btn"] = (*rgb, 35); TH["btnh"] = (*rgb, 65)
        if TH["name"] == "dark":
            TH["bg0"] = tuple(round(v * .42) for v in rgb); TH["bg1"] = tuple(round(b + v * .05) for b, v in zip((10, 17, 21), rgb))
            TH["dlg"] = QColor(round(25 + rgb[0] * .08), round(21 + rgb[1] * .08), round(29 + rgb[2] * .08)).name()
            # другорядний текст (статус, дні тижня, неактивні чати) — світлий відтінок кольору емоції
            TH["fg2"] = QColor(*(round(v + (255 - v) * .52) for v in rgb)).name()
        else:
            TH["bg0"] = tuple(round(255 * .90 + v * .10) for v in rgb); TH["bg1"] = tuple(round(255 * .95 + v * .05) for v in rgb)
            TH["dlg"] = QColor(round(255 * .96 + rgb[0] * .04), round(255 * .96 + rgb[1] * .04), round(255 * .96 + rgb[2] * .04)).name()
            # у світлій темі другорядний текст — НАСИЧЕНИЙ середній відтінок кольору емоції (не тусклий!)
            TH["fg2"] = QColor(*(round(v * .52 + d * .48) for v, d in zip(rgb, (95, 40, 62)))).name()
    def set_panel_target(self, color):
        to = (color.red(), color.green(), color.blue())
        if max(abs(a - b) for a, b in zip(self.pc, to)) < 1.5:
            self.pa = None      # вже на місці — скасовуємо і стару анімацію, щоб колір не «втік» до попередньої емоції
            return
        self.pa = (time.time(), tuple(self.pc), to)
    def step_panel(self, now):
        """Плавно (≈0.6 с, як і аура мордашки) змінюємо колір усієї панелі за емоцією."""
        if not self.pa: return
        t0, a, b = self.pa; k = clamp((now - t0) / .62, 0, 1); k = k * k * (3 - 2 * k)
        self.pc = [lerp(x, y, k) for x, y in zip(a, b)]; self.apply_rgb_theme()
        if k >= 1 or now - self._inp_t > .1:
            self._inp_t = now; self.style_input()
            self.status.setStyleSheet(f"color:{TH['fg2']}")   # статус теж кольору емоції, а не зашитий сіро-рожевий
        if k >= 1:
            self.pa = None
            if self.settings_open: self.settings.restyle()
        self.update()
        # діти малюють колір панелі у своїх paintEvent — без примусового repaint вони
        # лишаються «рожевими» після зміни емоції (бульбашки, календар, сегмент, кнопки)
        for w in (self.seg, self.menu_panel, self.chat_page, self.grip, self.attach_bar,
                  *self.bubbles, *self.cards, self.b_back, self.b_close, self.b_min,
                  self.b_gear, self.b_menu, self.b_theme):
            w.update()
    def apply_face_palette(self, emotion=None, to_base=False):
        if emotion is None and not to_base: emotion = self._queued_face_emotion[0]
        rgb = [int(clamp(int(v), 0, 255)) for v in self.cfg.get("face_rgb", DEFAULT_CFG["face_rgb"])]
        base = QColor(*rgb)      # основний колір — рожевий
        if not to_base and self.cfg.get("auto_emotion_color", False) and emotion:
            hue = {"happy": 330, "joy": 330, "playful": 330, "giggle": 330, "delighted": 330,
                   "sparkle": 278, "love": 330, "shy": 330, "tender": 330, "cozy": 330,
                   "sad": 215, "crying": 215, "hurt": 215, "worried": 265, "scared": 265, "fear": 265,
                   "angry": 4, "irritated": 4, "pout": 4, "surprised": 190, "shocked": 190,
                   "thinking": 330, "curious": 330, "calm": 330, "neutral": 330}.get(emotion, 330)
            base = QColor.fromHsv(hue, max(115, base.saturation()), max(180, base.value()))   # досить насичено — у світлій темі не тускніє
        self.set_panel_target(base)
        blush = QColor(int(lerp(base.red(), 255, .16)), int(lerp(base.green(), 255, .16)), int(lerp(base.blue(), 255, .16)))
        ink = "#161016" if self.cfg.get("theme") == "light" else "#ffffff"
        if self.face_view and self.face_view_ready:
            self.face_view.page().runJavaScript(f"window.luraSetPalette({json.dumps(base.name())},{json.dumps(blush.name())},{json.dumps(ink)})")
        self.update()
    def toggle_theme(self): self.set_theme_name("light" if self.cfg["theme"] == "dark" else "dark")
    def set_theme_name(self, n):
        if self.cfg["theme"] == n: return
        snapshot = self.grab()
        self.cfg["theme"] = n; jsave(CFG_P, self.cfg)
        self.pc = [float(v) for v in self.cfg["face_rgb"]]; self.pa = None      # нова тема стартує з чистого рожевого
        self.apply_theme(); self.settings.sync()
        if hasattr(self, "theme_snapshot"): self.theme_snapshot.fade_from(snapshot)
    def set_language(self, language):
        global LANG
        if language not in LANG_NAMES: return
        LANG = language; self.cfg["language"] = language; jsave(CFG_P, self.cfg)
        self.settings.retranslate(); self.settings.sync()
        self.seg.items = [T("API-хмара"), T("Локальна")]; self.seg.update()
        self.inp.setPlaceholderText(T("Напиши мені…"))
        self.eye.setToolTip({"en":"Include a screenshot with your message", "uk":"Показати Лурі екран разом із повідомленням", "ru":"Приложить снимок экрана к сообщению"}[LANG])
        for button, key in ((self.b_back,"Назад до чату"),(self.b_close,"Вийти"),(self.b_min,"Згорнути в кружечок"),(self.b_gear,"Налаштування"),(self.b_menu,"Меню — календар і чати"),(self.b_theme,"Світла / темна тема")):
            button.setToolTip(T(key))
        self.set_status(getattr(self, "status_raw", ""))
    def set_emoji_set(self, n):
        global EMOJI_SET
        EMOJI_SET = n; self.cfg["emoji_set"] = n; jsave(CFG_P, self.cfg); self.rerender()
    def set_provider(self, name):
        if self.cfg["provider"] == name: return
        if name not in ("cloud", "local"): return
        self.cfg["provider"] = name; jsave(CFG_P, self.cfg); self.refresh_provider_ui(); self.server.ensure()
    def set_character(self, name):
        if name not in ("restrained", "lively", "bright"): return
        self.cfg["emotionality"] = name; jsave(CFG_P, self.cfg)
    def set_cloud_provider(self, name):
        if name not in CLOUD_SERVICES: return
        self.cfg["cloud_provider"] = name; jsave(CFG_P, self.cfg)
        self.settings.fill_service_ui(); self.settings.update_groups(); self.refresh_provider_ui()
    def set_backend(self, name):
        if self.cfg["local_backend"] == name: return
        self.cfg["local_backend"] = name; jsave(CFG_P, self.cfg); self.settings.update_groups(); self.refresh_provider_ui(); self.server.ensure()
    def reset_pro(self): self.next_pro = time.time() + random.uniform(self.cfg["proactive_min"], self.cfg["proactive_max"]) * 60
    def build_tray(self):
        pm = QPixmap(64, 64); pm.fill(Qt.GlobalColor.transparent); p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(12, 18, 42)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(1, 1, 62, 62)
        old = dict(TH); set_theme("dark"); draw_face(p, QPointF(32, 32), .2, Face(), 0); TH.clear(); TH.update(old); p.end()
        self.tray = QSystemTrayIcon(QIcon(pm), self); m = QMenu()
        m.addAction(T("Показати / згорнути"), self.toggle); m.addAction(T("Новий чат"), self.new_chat); m.addAction(T("Пам'ять — павутина"), self.show_memory_web)
        m.addAction(T("Налаштування"), self.open_settings); m.addAction(T("Вийти"), self.quit_app)
        self.tray.setContextMenu(m); self.tray.activated.connect(lambda r: self.toggle() if r == QSystemTrayIcon.ActivationReason.Trigger else None); self.tray.show()
    def own_hwnds(self): return {int(self.winId()), int(self.toast.winId())}

    # ── чати (як у мобільній версії): новий / очистити / видалити / перемкнути
    def _new_chat_id(self): return f"{int(time.time() * 1000):x}-{random.randint(100, 999)}"
    def _chat_id(self): return str(self.cfg.get("chat_id", ""))
    def current_session(self): return next((s for s in self.sessions if s["id"] == self._chat_id()), self.sessions[0])
    def _save_chat(self):
        ses = self.current_session()
        if ses is not None:
            ses["messages"] = self.history[-80:]
            if not ses.get("title") or ses["title"] == "Новий чат":
                first = next((m["content"] for m in self.history if m.get("role") == "user"), "")
                if first: ses["title"] = first.strip()[:42]
            jsave(CHATS_P, self.sessions)
        jsave(HIST_P, self.history[-30:])
    def render_history(self):
        for lab in list(self.bubbles): lab.row.deleteLater()
        self.bubbles = []
        for card in list(self.cards): card.row.deleteLater()
        self.cards = []
        for m in self.history[-8:]:
            c = m["content"]
            if m["role"] == "user" and SYS_RE.match(c): continue
            if m["role"] == "assistant": self.add_bubble(split_tags(c)[0], "lura"); continue
            for pth in re.findall(r"\[\[файл:(.+?)\]\]", c): self.add_file_card(pth)
            txt = re.sub(r"\s*\[\[файл:.+?\]\]", "", c).strip()
            if txt: self.add_bubble(txt, "user")
    def new_chat(self):
        self._save_chat()
        self.sessions.append({"id": self._new_chat_id(), "title": "Новий чат", "created": time.time(), "messages": []})
        self.load_chat(self.sessions[-1]["id"])
        greet = NEW_CHAT_GREETING.get(LANG, NEW_CHAT_GREETING["uk"])
        self.history.append({"role": "assistant", "content": greet}); self.add_bubble(greet, "lura"); self._save_chat()
        self.flash_status(T("Новий чат"), 2200)
    def clear_chat(self):
        if ask_dialog(T("Очистити чат") + "?") not in ("yes", "always"): return
        self.history = []; self.render_history()
        greet = NEW_CHAT_GREETING.get(LANG, NEW_CHAT_GREETING["uk"])
        self.history.append({"role": "assistant", "content": greet}); self.add_bubble(greet, "lura"); self._save_chat()
        self.flash_status(T("Очистити чат") + " ✓", 2200)
    def delete_chat(self):
        if len(self.sessions) <= 1: self.clear_chat(); return
        if ask_dialog(T("Видалити чат") + "?") not in ("yes", "always"): return
        idx = next((i for i, s in enumerate(self.sessions) if s["id"] == self._chat_id()), 0)
        self.sessions.pop(idx)
        self.load_chat(self.sessions[max(0, idx - 1)]["id"])
        self.flash_status(T("Видалити чат") + " ✓", 2200)
    def load_chat(self, sid):
        self._save_chat()
        self.cfg["chat_id"] = sid; jsave(CFG_P, self.cfg)
        self.history = list(self.current_session().get("messages", []))[-30:]
        self.render_history(); self._save_chat(); self.scroll_bottom()

    # ── гладження і торкання мордашки (як у мобільній версії)
    def _face_zone(self, pos):
        """Коло мордашки у локальних координатах; поза ним — звичайне перетягування вікна."""
        if self.mode == "orb": return True
        if self.settings_open or pos.y() >= self.hdr_h() + 30: return False
        fc = self.face_center_local(); return math.hypot(pos.x() - fc.x(), pos.y() - fc.y()) < max(60, self.face_scale() * 110)
    def _pet_start(self, gpos):
        self._pet = {"x": gpos.x(), "y": gpos.y(), "lastX": gpos.x(), "lastDx": 0, "turns": 0, "moved": 0.0, "petting": False}
    def _pet_move(self, gpos):
        pet = self._pet
        dx = gpos.x() - pet["lastX"]
        if abs(dx) > 4:
            if pet["lastDx"] != 0 and (dx > 0) != (pet["lastDx"] > 0): pet["turns"] += 1
            pet["lastDx"] = dx
        pet["lastX"] = gpos.x()
        pet["moved"] = max(pet["moved"], math.hypot(gpos.x() - pet["x"], gpos.y() - pet["y"]))
        if not pet["petting"] and pet["turns"] >= 2 and 16 < pet["moved"] < 40:
            pet["petting"] = True
            self.set_face_emotion("cozy:0.6,happy:0.4", 5)
            self.pet_chat()
        return pet["petting"]
    def pet_chat(self):
        if time.time() - self._last_pet < 7: return          # не частіше, ніж раз на 7 с
        self._last_pet = time.time()
        line = pet_line()
        self.add_bubble(line, "lura")
        self.history.append({"role": "assistant", "content": line}); self.history = self.history[-30:]
        self._save_chat(); self.scroll_bottom()
        self.set_face_emotion("shy", 4)
    def face_tap(self, nx, ny):
        """Торкання по мордашці: зони, як у мобільній версії (згори — злилась, знизу — смішно/затишно)."""
        if ny < .33: emo = "angry"
        elif ny < .62: emo = "surprised" if (nx < .38 or nx > .62) else "curious"
        elif .4 < nx < .6: emo = "giggle"
        else: emo = "cozy" if (nx < .38 or nx > .62) else "inquisitive"
        self.set_face_emotion(emo, 2.4)
    def show_memory_web(self):
        w = MemoryWeb(self); w.move(self.x() - w.width() - 12, max(0, self.y() + 40)); w.show(); self._mem_web = w
    def open_menu_panel(self):
        """Меню — не окреме вікно: основне вікно Лури плавно розширюється вліво,
        і в новій колонці з'являються календар, нагадування та чати."""
        if self.menu_open or self.animating() or self.resizing: return
        if self.mode == "orb": self.expand(); return
        self.menu_open = True
        ag = (QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()).availableGeometry()
        left = max(ag.left() + 4, self.x() - MENU_W)
        grow = self.x() - left
        self._menu_back = QRect(left, self.y(), self.width() + grow, self.height())
        self.menu_anim.stop()
        self.menu_anim.setStartValue(self.geometry()); self.menu_anim.setEndValue(self._menu_back); self.menu_anim.start()
    def close_menu_panel(self):
        if not self.menu_open: return
        self.menu_open = False
        grow = max(0, self.width() - self.cw)
        self.menu_anim.stop()
        self.menu_anim.setStartValue(self.geometry())
        self.menu_anim.setEndValue(QRect(self.x() + grow, self.y(), self.cw, self.height())); self.menu_anim.start()
    def toggle_menu_panel(self): self.close_menu_panel() if self.menu_open else self.open_menu_panel()
    def _menu_anim_done(self):
        if not self.menu_open:
            self.menu_panel.hide()
            self.chat_rect = QRect(self.x(), self.y(), self.cw, self.ch)   # самовідновлення: меню закрите — геометрія знову «чат»
        self.layout_body()
    def menu_w(self):
        """Поточна ширина колонки меню (0 — коли схована; під час анімації — проміжна)."""
        if not (self.menu_open or self.menu_anim.state() == QPropertyAnimation.State.Running): return 0
        return max(0, min(MENU_W, self.width() - self.cw))
    def remove_chat(self, sid):
        """Видалити чат за id (поточний проходить через delete_chat із підтвердженням)."""
        if sid == self._chat_id(): self.delete_chat(); return
        self.sessions[:] = [s for s in self.sessions if s["id"] != sid]
        self._save_chat()

    # ── бульбашки
    def style_bubble(self, lab):
        if getattr(lab, "big", False): lab.setStyleSheet("background:transparent;padding:0 4px")
        elif lab.role == "user": lab.setStyleSheet(f"background:transparent;color:{TH['ufg']};padding:9px 13px")   # фон малює Bubble.paintEvent
        else: lab.setStyleSheet(f"background:{rgba(TH['bub'])};color:{TH['fg']};border-radius:17px;padding:9px 13px")
        lab.setFont(ufont(14))
    def set_bubble(self, lab, text):
        lab.raw = text; big = bool(ONLY_EMO.match(text.strip())) if text.strip() else False
        if big != getattr(lab, "big", False): lab.big = big; self.style_bubble(lab)
        lab.setText(to_html(text, 40 if big else 20)[0])
    def rerender_soon(self): self.re_t.start(250)
    def rerender(self):
        for lab in self.bubbles:
            if hasattr(lab, "raw"): self.set_bubble(lab, lab.raw)
    def add_bubble(self, text, role):
        lab = Bubble(role); lab.setWordWrap(True); lab.setMaximumWidth(int(self.cw * .76)); lab.setOpenExternalLinks(True)
        lab.setTextFormat(Qt.TextFormat.RichText); lab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.style_bubble(lab); self.set_bubble(lab, text); self.bubbles.append(lab)
        rw = QWidget(); r = QHBoxLayout(rw); r.setContentsMargins(0, 0, 0, 0)
        if role == "user": r.addStretch(1)
        r.addWidget(lab)
        if role != "user": r.addStretch(1)
        self.mv.addWidget(rw); lab.row = rw; self.scroll_bottom(); return lab
    def remove_bubble(self, lab):
        if lab in self.bubbles: self.bubbles.remove(lab)
        lab.row.deleteLater()
    def show_typing(self):
        if self.typing_row: return
        rw = QWidget(); r = QHBoxLayout(rw); r.setContentsMargins(0, 0, 0, 0); self.typing = Typing(); r.addWidget(self.typing); r.addStretch(1)
        self.mv.addWidget(rw); self.typing_row = rw; self.scroll_bottom()
    def hide_typing(self):
        if self.typing_row: self.typing_row.deleteLater(); self.typing_row = None
    def scroll_bottom(self): QTimer.singleShot(30, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))
    def set_status(self, t=""):
        shown = t or self.sticky
        self.status_raw = shown
        if not shown or self.mode == "orb": self.status.setText(""); return   # у кружечку статус лише обрізався б по краях
        text = f"✦ {T(shown)}"
        if self.status.width() > 60:
            fm = QFontMetrics(self.status.font())
            text = fm.elidedText(text, Qt.TextElideMode.ElideRight, self.status.width() - 12)
        self.status.setText(text)
    def set_sticky(self, m): self.sticky = m; self.set_status("" if not self.busy else getattr(self, "status_raw", ""))

    # ── діалог з моделлю (зі стрімінгом)
    def configured(self):
        if self.cfg.get("provider") == "local": return True
        svc = api_provider(self.cfg)
        if svc == "google":
            try: return bool(load_google_keys(self.cfg))
            except Exception: return False
        return bool(svc_key(self.cfg, svc))
    def style_modifiers(self):
        """Блок «поточні налаштування характеру» в системний промт — мовою з prompts.json."""
        c = self.cfg; sm = P("style_modifiers")
        b = "\r\n\r\n" + sm.get("header", "ХАРАКТЕР") + ":\r\n"
        emo = c.get("emotionality", "lively")
        b += "- " + sm.get(emo, sm.get("lively", "")) + "\r\n"
        b += "- " + sm.get("sarcasm_on" if c.get("sarcasm", True) else "sarcasm_off", "") + "\r\n"
        b += "- " + sm.get("hurt_on" if c.get("hurt", True) else "hurt_off", "") + "\r\n"
        if c.get("user_name"): b += "- " + sm.get("name", "{name}").replace("{name}", str(c["user_name"])) + "\r\n"
        return b
    def build_system(self):
        pr, m = P(), P("misc")
        with self.lock: rem = "\r\n".join(f"#{r['id']} {dt.datetime.fromtimestamp(r['due']):%m-%d %H:%M} {r['text']}" for r in self.rem) or m.get("no_rems", "(немає)")
        c = self.cfg
        facts = "\r\n".join(f"- {k}: {v}" for k, v in self.mem["facts"].items()) or m.get("no_facts", "(поки нічого)")
        prefs = "\r\n".join(f"- #{x['id']} {x['text']}" for x in self.mem["prefs"]) or m.get("no_prefs", "(жодних)")
        pro = (m.get("pro_active", "так").replace("{a}", str(c["proactive_min"])).replace("{b}", str(c["proactive_max"]))
               if c["proactive"] else m.get("pro_off", "НІ"))
        snd = m.get("yes", "так") if c["sound"] else m.get("no", "ні")
        cmds = ", ".join(c.get("allowed_cmds", [])) or m.get("no_cmds", "(жодних)")
        persona = (P("persona").replace("{emotions}", ", ".join(PRESETS)).replace("{shortcuts}", c["shortcuts_dir"])
                   + self.style_modifiers())
        profile = (P("profile")
                   .replace("{now}", f"{dt.datetime.now():%A %Y-%m-%d %H:%M}").replace("{os}", platform.system())
                   .replace("{user}", c["user_name"] or m.get("no_name", "(невідоме)"))
                   .replace("{facts}", facts).replace("{prefs}", prefs).replace("{pro}", pro)
                   .replace("{snd}", snd).replace("{cmds}", cmds).replace("{rem}", rem))
        # мовне правило — останній рядок усього промту: моделі найсильніше слухають кінець
        return persona + "\r\n\r\n" + profile + "\r\n" + P("lang_rule")
    def touch(self):
        was = self.miss_level; self.last_touch = time.time(); self.miss_level = 0; self.face.base_spec = "happy"
        if was >= 2: self.set_face_emotion("happy:.7,surprised:.3", 4)
    def on_send(self):
        t = self.inp.toPlainText().strip(); files = list(self.attachments)
        if not t and not files: return
        if self.busy: self.set_status(T("зачекай, я ще думаю…")); return
        self.inp.clear(); self.touch(); self._user_touched = True; img = None
        emo = detect_user_emotion(t or "")
        if emo:                                          # реакція на настрій користувача одразу, як у мобільній версії
            neg = emo in ("angry", "hurt", "sad", "irritated")
            self._user_emotion, self._user_emotion_until = emo, time.time() + (14 if neg else 9)
            self.set_face_emotion(emo, 14 if neg else 9)
        else: self._user_emotion = None
        if self.eye.isChecked():
            r = self.grab_screen(); self.eye.setChecked(False)
            if isinstance(r, tuple): img = r[0]; self.tools.last_shot = r[1]
        self.attachments.clear(); self.attach_bar.set_files([])
        for f in files: self.add_file_card(f)
        if t or img: self.add_bubble(t + ("\r\n(з екраном)" if img else ""), "user")
        if not self.configured():
            self.set_face_emotion(local_emotion(t or "файл"), 4)
            self.add_bubble(T("Я відреагувала настрієм офлайн. Для текстової відповіді під'єднай модель у налаштуваннях."), "lura")
            return
        text, file_imgs = self.prepare_attachments(t, files)
        imgs = ([img] if img else []) + file_imgs
        self.start_worker((text or " ").strip(), imgs)

    def prepare_attachments(self, text, files):
        """Прикріплені файли майже будь-яких типів: картинки → у зір, текст/PDF/DOCX → вміст у повідомлення,
        бінарники → картка-тег [[файл:]]."""
        imgs = []
        for f in files:
            ext = f.suffix.lower()
            if ext in IMG_EXT and len(imgs) < 4:
                data = read_image_data_url(f)
                if data: imgs.append(data); continue
            content = read_file_content(f)
            if content is not None: text = (text or "") + f"\r\n\r\n[файл: {f.name}]\r\n{content}"
            else: text = (text or "") + f"\r\n[[файл:{f}]]"
        return text, imgs
    def system_turn(self, note, fallback=None):
        if self.busy: return False
        mark = P("svc_mark") or "[службове] "   # префікс службових нотаток — мовою промту
        self._fallback = fallback; self.start_worker(mark + note, None, True); return True
    def new_stream(self): return dict(lab=None, applied=0, t=0.0)
    def start_worker(self, text, imgs=None, system=False):
        self.busy = True; self.stream = self.new_stream(); self.face.base_spec = "neutral"; self.face.typing = True; self.face.talking = False
        self.set_face_mode("listen",False); self.set_face_mode("think",True)
        # як у мобільній версії: коли користувач образив/розсердив її — «думаю» не перебиває цей вираз
        if not (self._user_emotion in ("angry", "hurt", "sad") and time.time() < self._user_emotion_until):
            self.set_face_emotion("thinking",0)
        self.set_status(T("думаю…"))
        if self.mode == "chat": self.show_typing()
        imgs = imgs or []
        if imgs:      # скріншот і/або прикріплені картинки — спільний список зображень
            content = [{"type": "text", "text": text or T("Ось файли:")}]
            for b64 in imgs:
                url = b64 if b64.startswith("data:") else "data:image/jpeg;base64," + b64
                content.append({"type": "image_url", "image_url": {"url": url}})
        else: content = text
        w = Worker(self, list(self.history), content); w.status.connect(self.set_status); w.delta.connect(self.on_delta); w.newround.connect(self.on_newround)
        w.ok.connect(lambda r: self.on_reply(r, text + (f" [{len(imgs)} зобр.]" if imgs else ""), system)); w.err.connect(lambda e: self.on_error(e, system))
        self.worker = w; w.start()
    def on_newround(self):
        st = self.stream
        if st["lab"] is not None and st.get("plain"): self.set_bubble(st["lab"], st["plain"])
        self.stream = self.new_stream()
        if self.mode == "chat": self.show_typing()
    def on_delta(self, raw):
        plain, ev = partial_plain(raw); st = self.stream
        if plain and st["lab"] is None: self.set_face_emotion("neutral", 0)   # вона почала писати — базовий «друкуючий» вираз; усмішка повернеться після відповіді
        if self.mode != "chat": return
        if st["lab"] is None:
            if not plain: return
            self.hide_typing(); st["lab"] = self.add_bubble("", "lura")
        # Під час набору лишаємо мордашку нейтральною; емоції відповіді застосуємо після завершення.
        now = time.time(); self.face.talking = False; st["plain"] = plain
        if now - st["t"] > .04: self.set_bubble(st["lab"], plain); st["t"] = now; self.scroll_bottom()
    def on_reply(self, raw, user_text, system):
        self.hide_typing(); plain, ev = split_tags(raw); st = self.stream
        skipped = any(s.strip().lower() == "skip" for _, s in ev)
        if skipped or (system and not plain):
            if st["lab"] is not None: self.remove_bubble(st["lab"])
            self.stream = self.new_stream(); self.busy = False; self.set_status("")
            self.face.typing = False; self.face.talking = False; self.set_face_mode("think",False)
            if not skipped and self._fallback:      # модель промовчала на служове повідомлення — показуємо запасний текст
                fb = self._fallback; self._fallback = None; self.deliver(*split_tags(fb))
            else:
                self.face.base_spec = "happy"; self.set_face_emotion(self.face.base_spec, 0)
            return
        self.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": raw}]; self.history = self.history[-30:]
        while self.history and self.history[0]["role"] != "user": self.history.pop(0)
        self._save_chat()
        self.face.typing = False; self.set_face_mode("think",False); self.face.base_spec = "happy"; self._fallback = None
        if st["lab"] is not None:           # відповідь вже стрімилась у чат — просто дописуємо кінець
            self.set_bubble(st["lab"], plain); st["applied"] = len(ev)
            if ev:
                for _, s in ev: self.set_face_emotion(s, 9)
            elif self._user_emotion and time.time() < self._user_emotion_until:   # тримаємо емоцію користувача, як у мобільній
                self.set_face_emotion(self._user_emotion, 6)
            else: self.set_face_emotion("happy", 6)
            if self.face_view and self.face_view_ready:self.face_view.page().runJavaScript(f"window.luraSpeak({json.dumps(plain[:600])})")
            self.face.talking = False; self.busy = False; self.set_status("")
            if self.mode == "orb" or not self.isVisible(): self.notify_orb(plain)
            self.scroll_bottom()
        else: self.deliver(plain, ev)
        self.stream = self.new_stream()
    def on_error(self, msg, system):
        self.hide_typing(); self.busy = False; self.face.typing = False; self.face.talking = False; self.set_face_mode("think",False)
        self.face.base_spec = "happy"; self.set_status(""); self.set_face_emotion("sad", 8)
        if system:
            if self._fallback:        # у службової репліки є запасний текст — показуємо його
                fb = self._fallback; self._fallback = None; self.deliver(*split_tags(fb)); return
            # без запасного тексту (напр., ініціатива) — показуємо помилку, щоб повідомлення не губились мовчки
        backend = api_provider(self.cfg)
        if backend == "google" and ("429" in msg or "quota" in msg.lower()):
            msg = {"uk": "Google Gemini вичерпав квоту або ліміт запитів для всіх ключів у keys.txt. Перевір квоти ключів або додай інші ключі.",
                   "en": "Google Gemini quota or request limits were reached for all keys in keys.txt. Check the key quotas or add more keys.",
                   "ru": "Для всех ключей в keys.txt исчерпана квота или лимит запросов Google Gemini. Проверь квоты ключей или добавь другие ключи."}.get(LANG, "Google Gemini вичерпав квоту для всіх ключів у keys.txt.")
        elif backend == "openrouter" and "free-models-per-day" in msg.lower():
            msg = {
                "uk": "OpenRouter вичерпав денний ліміт безкоштовних моделей. Дочекайся скидання ліміту або вибери платну модель у налаштуваннях і поповни баланс OpenRouter.",
                "en": "OpenRouter's daily limit for free models has been reached. Wait for the limit to reset, or choose a paid model in Settings and add credits to your OpenRouter balance.",
                "ru": "Дневной лимит бесплатных моделей OpenRouter исчерпан. Дождись сброса лимита или выбери платную модель в настройках и пополни баланс OpenRouter.",
            }.get(LANG, "OpenRouter вичерпав денний ліміт безкоштовних моделей. Дочекайся скидання ліміту або вибери платну модель у налаштуваннях і поповни баланс OpenRouter.")
        elif backend == "openrouter" and (msg.startswith("404") or "No endpoints found" in msg):
            model = self.cfg.get("openrouter_model", "").strip()
            msg = {"uk": f"OpenRouter не знайшов модель «{model}» (404). Перевір її назву в налаштуваннях; стандартна модель Лури — google/gemini-3.8-flash.",
                   "ru": f"OpenRouter не нашёл модель «{model}» (404). Проверь её название в настройках; стандартная модель Луры — google/gemini-3.8-flash.",
                   "en": f"OpenRouter could not find the model «{model}» (404). Check its name in Settings; Lura's default model is google/gemini-3.8-flash."}.get(LANG, "")
        if self.cfg["provider"] == "local" and any(k in msg for k in ("Connection", "refused", "503", "Max retries")):
            msg = {"uk": "локальний сервер ще не готовий — зачекай, поки внизу зникне напис про завантаження.",
                   "ru": "локальный сервер ещё не готов — подожди, пока внизу исчезнет надпись о загрузке.",
                   "en": "the local server isn't ready yet — wait until the loading note at the bottom disappears."}.get(LANG, "")
        if "exceeds the available context" in msg or "context size" in msg.lower() or "maximum context" in msg.lower() or "too many tokens" in msg.lower():
            self.history = self.history[-6:]; jsave(HIST_P, self.history)   # обрізаємо стару розмову — наступний запит поміститься
            msg = {"uk": "контекст моделі переповнився. Я прибрала найстарішу частину нашої розмови — напиши ще раз, тепер має поміститись.",
                   "en": "The model context overflowed. I trimmed the oldest part of our conversation — send it again, it should fit now.",
                   "ru": "Контекст модели переполнен. Я убрала самую старую часть нашего разговора — напиши ещё раз, теперь должно поместиться."}.get(LANG, "контекст моделі переповнився — я обрізала стару частину розмови, спробуй ще раз")
        self.add_bubble("Помилка: " + msg, "lura")
    def notify_orb(self, plain):          # звук і сповіщення — лише коли Лура згорнута в кружечок
        self.unread = True; self.toast.pop(plain, self.geometry()); self.play_ping()
        self.face.talking = True; QTimer.singleShot(1500, lambda: setattr(self.face, "talking", False))
    def play_ping(self):
        if not self.cfg["sound"]: return
        if self.ping is not None: self.ping.play()
        else: QApplication.beep()
    def deliver(self, plain, ev):
        if not ev: ev = [(0, next((v for k, v in EMO.items() if k in plain), "happy:.5"))]
        self.busy = False; self.set_status(""); self.face.base_spec = "happy"
        self.add_bubble(plain, "lura"); self.set_face_emotion(ev[-1][1], 9)
        if self.face_view and self.face_view_ready:self.face_view.page().runJavaScript(f"window.luraSpeak({json.dumps(plain[:600])})")
        if self.mode == "orb" or not self.isVisible(): self.notify_orb(plain)

    def grab_screen(self, max_w=1600):
        self.setWindowOpacity(0.0); QApplication.processEvents(); QThread.msleep(130); QApplication.processEvents()
        pm = QGuiApplication.primaryScreen().grabWindow(0); self.setWindowOpacity(1.0)
        real = (pm.width(), pm.height())
        if pm.width() > max_w: pm = pm.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
        buf = QBuffer(); buf.open(QIODevice.OpenModeFlag.WriteOnly); pm.save(buf, "JPEG", 72)
        return base64.b64encode(bytes(buf.data())).decode(), (pm.width(), pm.height()), real

    # ── цикли
    def tick(self):
        now = time.time(); d = min(now - self._last, .1); self._last = now
        if self._pal_reset_at and now > self._pal_reset_at and not self.busy:
            self._pal_reset_at = 0.0; self.apply_face_palette(to_base=True)   # після емоції — назад у рожевий
            if not self.face.hold_until and not self.face.talking: self.set_face_emotion(self.face.base_spec or "happy", 0)
        if self.mode == "orb" and self._morph > .99 and self.body.isVisible(): self.body.hide()
        if not self.face_view_ready:
            fc = self.face_center_local(); cur = QCursor.pos()
            vx, vy = cur.x() - (self.x() + fc.x()), cur.y() - (self.y() + fc.y())
            self.face.step(now, d, (math.tanh(vx / 260), math.tanh(vy / 260)))
        if self.face.talking and self.stream["lab"] is not None and now > self.talk_until: self.face.talking = False
        self.step_panel(now)
        if not self.resizing:
            tgt = 1.0 if self.target_compact() else 0.0
            if abs(self.hc - tgt) > .003 and not self.animating():
                self.hc += (tgt - self.hc) * (1 - math.exp(-d * 9)); self.hc = tgt if abs(self.hc - tgt) < .004 else self.hc; self.layout_body()
            self.sync_face_compact()
        if self.face_view_ready:
            if self.typing_row: self.typing.update()
        elif self.typing_row: self.typing.update()
        if self.face_view_ready:
            return
        if self.mode == "chat" and not self.animating() and self.isVisible():
            self.chat_page.update(); self.update(0, 0, self.width(), int(self.hdr_h()) + 50)
        else: self.update()
    def slow(self):
        now = time.time(); idle = now - self.last_touch
        if not self.busy:
            with self.lock: due = [r for r in self.rem if r["due"] <= now]
            if due:   # нагадування спрацьовують ЗАВЖДИ — навіть якщо «не писати першою»
                r = due[0]
                with self.lock:
                    if r.get("repeat"): r["due"] = now + r["repeat"] * 60
                    else: self.rem.remove(r)
                    jsave(REM_P, self.rem)
                self.system_turn(P("note_reminder").replace("{text}", r["text"]),
                                 fallback=f"[[excited]] {P('word_reminder')}: {r['text']}"); return
            if self.cfg["proactive"] and self.configured() and idle > 180 and now > self.next_pro:
                self.reset_pro()
                note = (P("note_proactive").replace("{time}", dt.datetime.now().strftime("%H:%M"))
                        .replace("{mins}", str(int(idle // 60))))
                self.system_turn(note)
        miss = clamp((idle - 600) / 1800, 0, 1); lvl = int(miss * 8)     # сумує, коли їй давно не пишуть
        self.face.base_spec = f"sad:{.8 * miss:.2f}" if lvl > 0 else "happy"
        if lvl != self.miss_level and not self.busy and not self.face.hold_until and not self.face.talking:
            self.miss_level = lvl; self.set_face_emotion(self.face.base_spec, hold=0)

    # ── малювання
    def glow_color(self): return QColor(*[int(clamp(round(v), 0, 255)) for v in self.pc])
    def paint_bg(self, p):
        t, w, h = self._morph, self.width(), self.height(); rad = lerp(24, min(w, h) / 2, t); hce = self.hc * (1 - t)
        path = QPainterPath(); path.addRoundedRect(QRectF(1, 1, w - 2, h - 2), rad, rad)
        g = QLinearGradient(0, 0, 0, h); g.setColorAt(0, QColor(*TH["bg0"])); g.setColorAt(1, QColor(*TH["bg1"])); p.fillPath(path, g)
        col = self.glow_color(); fc = self.face_center_local(); p.save(); p.setClipPath(path)
        rg = QRadialGradient(fc, lerp(lerp(230, 150, self.hc), 70, t) * (self.ow / 84 if t > .5 else 1)); c1 = QColor(col); c1.setAlpha(int(TH["glow"] * (1 - .75 * hce))); c0 = QColor(col); c0.setAlpha(0)
        rg.setColorAt(0, c1); rg.setColorAt(1, c0); p.fillRect(self.rect(), QBrush(rg)); p.restore(); return path
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); now = time.time(); t = self._morph
        path = self.paint_bg(p); fc = self.face_center_local(); st = self.face.cur; hce = self.hc * (1 - t)
        bc = QColor(*TH["border"]); bc.setAlpha(int(lerp(45, 150, t) + (70 * abs(math.sin(now * 3)) if self.busy and t > .9 else 0)))
        p.setPen(QPen(bc, 1.6)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
        if hce > .02:    # «віконечко» з мордашкою (компактний режим / налаштування)
            pill = QRectF(12 + 38 * self._sp, 10, PW, PH); pp = QPainterPath(); pp.addRoundedRect(pill, PH / 2, PH / 2)
            p.save(); p.setOpacity(hce); p.fillPath(pp, QColor(*TH["pill"])); p.setClipPath(pp)
            gc = self.glow_color(); gc2 = QColor(gc); gc2.setAlpha(int(TH["glow"] * .8)); g0 = QColor(gc); g0.setAlpha(0)
            rg = QRadialGradient(fc, PW * .6); rg.setColorAt(0, gc2); rg.setColorAt(1, g0); p.fillRect(pill, QBrush(rg)); p.setClipping(False)
            bc2 = QColor(*TH["border"]); bc2.setAlpha(90); p.setPen(QPen(bc2, 1.3)); p.drawPath(pp); p.restore()
        if not self.face_view_ready and st["hearts"] > .05 and t < .6 and self.hc < .5:   # fallback для систем без WebEngine
            hc = QColor(*TH["hatch"])
            for i in range(10):
                ph = (now * .12 + i / 10) % 1; seed = ((i * 7919) % 97) / 97
                x = fc.x() + (seed - .5) * self.width() * .85; y = fc.y() + 55 - ph * 110
                hc.setAlpha(int(230 * clamp(st["hearts"], 0, 1) * math.sin(math.pi * ph) * (1 - t)))
                p.save(); p.translate(x, y); p.setPen(QPen(hc, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
                if i % 3: p.drawPath(heart_path(2.4 + (i % 3) * 1.3))
                else: p.setBrush(hc); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(0, 0), 1.8, 1.8)
                p.restore()
        if not self.face_view_ready: draw_face(p, fc, self.face_scale(), self.face, now)
        if self.unread and t > .9:
            p.setPen(QPen(QColor(*TH["bg0"]), 2)); p.setBrush(QColor(255, 80, 130)); p.drawEllipse(QPointF(self.width() - 14, 14), 7, 7)

    # ── плавна зміна розміру: Chromium і бульбашки заморожуються, поки тягнемо
    def begin_resize(self, ed, gpos):
        if self.mode != "chat" or self.animating() or self.resizing or self.menu_open: return
        self.resizing = True; self._rs = (ed, QRect(self.geometry()), gpos); self._rs_pending = None; self._rs_last = 0.0
        bar = self.scroll.verticalScrollBar(); self._was_bottom = bar.value() >= bar.maximum() - 4
        for sa in (self.scroll, self.settings): sa.setWidgetResizable(False)   # без перерахунку тексту на кожному кадрі
        self.grip.update()
    def resize_move(self, gpos):
        if not self._rs: return
        ed, g, p0 = self._rs; d = gpos - p0; x, y, w, h = g.x(), g.y(), g.width(), g.height()
        if "l" in ed: nw = int(clamp(w - d.x(), MIN_W, MAX_W)); x = x + w - nw; w = nw
        if "r" in ed: w = int(clamp(w + d.x(), MIN_W, MAX_W))
        if "b" in ed: h = int(clamp(h + d.y(), MIN_H, MAX_H))
        self._rs_pending = (x, y, w, h)
        if time.perf_counter() - self._rs_last >= .012: self._rs_flush()      # не частіше ~80 разів/с
        elif not self.rs_timer.isActive(): self.rs_timer.start(12)
    def _rs_flush(self):
        g = self._rs_pending
        if not g or not self.resizing: return
        self._rs_pending = None; self._rs_last = time.perf_counter(); self.setGeometry(*g)
    def end_resize(self):
        if not self.resizing: return
        self.rs_timer.stop(); self._rs_flush(); self.resizing = False; self._rs = None
        for sa in (self.scroll, self.settings): sa.setWidgetResizable(True)
        self.cw, self.ch = self.width(), self.height(); self.chat_rect = self.geometry()
        self.layout_body()
        if self._was_bottom: self.scroll_bottom()
        self.grip.update()
        self.cfg["chat_w"], self.cfg["chat_h"] = self.cw, self.ch; jsave(CFG_P, self.cfg)

    # ── прикріплення файлів (без перетворення в текст)
    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, T("Прикріпити файл"))
        if files: self.add_attachments([Path(f) for f in files])
    def add_attachments(self, files):
        for f in files:
            f = Path(f)
            if f.is_file() and f not in self.attachments and len(self.attachments) < 8: self.attachments.append(f)
        self.attach_bar.set_files(self.attachments); self.scroll_bottom()
    def remove_attachment(self, i):
        if 0 <= i < len(self.attachments): self.attachments.pop(i)
        self.attach_bar.set_files(self.attachments)
    def add_file_card(self, path):
        card = FileCard(path); card.setMaximumWidth(int(self.cw * .76)); self.cards.append(card)
        rw = QWidget(); r = QHBoxLayout(rw); r.setContentsMargins(0, 0, 0, 0); r.addStretch(1); r.addWidget(card)
        self.mv.addWidget(rw); card.row = rw; self.scroll_bottom(); return card

    # ── перетягування файлів у вікно (шрифт — змінити шрифт, решта — прикріпити)
    def disable_child_drops(self):
        """Поля вводу самі «з'їдають» файли — вимикаємо, щоб подія дійшла до вікна."""
        for w in self.findChildren((QLineEdit, QPlainTextEdit)):
            w.setAcceptDrops(False)
            if isinstance(w, QPlainTextEdit): w.viewport().setAcceptDrops(False)
    def dragEnterEvent(self, e):
        files = dropped_files(e.mimeData())
        if not files: e.ignore(); return
        self.drop_hint.text = "Відпусти файл шрифту тут" if all(f.suffix.lower() in FONT_EXT for f in files) else "Відпусти файли тут, щоб прикріпити"
        self.drop_hint.setGeometry(self.rect()); self.drop_hint.raise_(); self.drop_hint.show(); self.drop_hint.update(); e.acceptProposedAction()
    def dragLeaveEvent(self, e): self.drop_hint.hide()
    def dropEvent(self, e):
        self.drop_hint.hide(); files = dropped_files(e.mimeData())
        if not files: return
        e.acceptProposedAction()
        if all(f.suffix.lower() in FONT_EXT for f in files): self.apply_font_files(files)
        else:
            if self.mode == "orb": self.expand()
            self.add_attachments(files)
    def flash_status(self, msg, ms=4000):
        self.set_sticky(msg); QTimer.singleShot(ms, lambda: self.set_sticky("") if self.sticky == msg else None)
    def apply_font_files(self, files):
        """Скопіювати шрифт у папку fonts поруч зі скриптом, встановити для програми й запам'ятати."""
        global FONT
        dest = APP_DIR / "fonts"
        try: dest.mkdir(exist_ok=True)
        except OSError: dest = FONT_DIR; dest.mkdir(exist_ok=True)
        families = []
        for f in files:
            target = dest / f.name
            try:
                if f.resolve() != target.resolve(): shutil.copy2(f, target)
            except OSError:
                try: FONT_DIR.mkdir(exist_ok=True); target = FONT_DIR / f.name; shutil.copy2(f, target)
                except OSError: target = f           # не вдалося скопіювати — користуємось файлом на місці
            fid = QFontDatabase.addApplicationFont(str(target))
            if fid >= 0: families.extend(QFontDatabase.applicationFontFamilies(fid))
        if not families: self.flash_status(T("не вдалося прочитати шрифт")); return
        FONT = families[0]; self.cfg["font"] = FONT; jsave(CFG_P, self.cfg)
        QApplication.instance().setFont(ufont(14)); self.apply_theme()
        for key, le, num in self.settings.edits:
            if key == "font": le.setText(FONT)
        self.set_face_emotion("happy:.7,sparkle:.3", 3); self.flash_status(T("шрифт змінено") + f": {FONT}")

    # ── мишка: перетягування, розмір, клік по мордашці
    def face_click(self, pos): return False
    def edges_at(self, pos):
        if self.mode != "chat" or self.animating(): return ""
        m, s = 8, ""
        if pos.x() < m: s += "l"
        if pos.x() > self.width() - m: s += "r"
        if pos.y() > self.height() - m: s += "b"
        return s
    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self.animating(): return
        self._press = e.globalPosition().toPoint(); self._wpos = self.pos(); self._moved = False; self._ppos = e.position().toPoint()
        ed = self.edges_at(self._ppos)
        if ed: self.begin_resize(ed, self._press); return
        face_zone = self._face_zone(self._ppos)
        if face_zone: self._pet_start(self._press)            # погладжування = рух туди-сюди по мордашці
        self._can_drag = (self.mode == "orb" or e.position().y() < self.hdr_h()) and not (face_zone and self.mode == "chat")
    def mouseMoveEvent(self, e):
        if self._press is None:
            ed = self.edges_at(e.position().toPoint())
            cur = {"lb": Qt.CursorShape.SizeBDiagCursor, "rb": Qt.CursorShape.SizeFDiagCursor, "l": Qt.CursorShape.SizeHorCursor,
                   "r": Qt.CursorShape.SizeHorCursor, "b": Qt.CursorShape.SizeVerCursor}.get(ed)
            self.setCursor(cur) if cur else self.unsetCursor(); return
        d = e.globalPosition().toPoint() - self._press
        if self.resizing: self.resize_move(e.globalPosition().toPoint()); return
        if self._pet is not None and self._pet_move(e.globalPosition().toPoint()): return   # гладимо — вікно не рухається
        if not self._can_drag: return
        if self.mode == "orb" and d.manhattanLength() < 12: return   # спершу зрозуміло: перетягування чи погладжування
        if d.manhattanLength() > 5: self._moved = True
        if self._moved:
            self.move(self._wpos + d)
            if self.mode == "orb": self.orb_rect = self.geometry()
            # з меню чат-прямокутник має лишатись «звуженим» — інакше після закриття меню лице з'їде вліво
            else: self.chat_rect = QRect(self.x() + self.menu_w(), self.y(), self.cw, self.ch)
    def mouseReleaseEvent(self, e):
        if self.resizing: self.end_resize(); self._press = None; return
        pet, self._pet = self._pet, None
        if pet is not None and pet["petting"]: self._press = None; self._rs = None; return   # погладили — не розгортаємо
        if pet is not None and pet["moved"] < 12 and self.mode == "chat":
            fc = self.face_center_local(); r = max(60, self.face_scale() * 110); pos = e.position().toPoint()
            self.face_tap(clamp((pos.x() - fc.x()) / (2 * r) + .5, 0, 1), clamp((pos.y() - fc.y()) / (2 * r) + .5, 0, 1))
            self._press = None; self._rs = None; return
        if self._press is not None and e.button() == Qt.MouseButton.LeftButton and not self._moved and not self._rs:
            if self.mode == "orb": self.expand()
            elif self._can_drag: self.face_click(e.position().toPoint())
        self._press = None; self._rs = None
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.mode == "chat" and not self.animating() and not self.menu_open and self.menu_anim.state() != QPropertyAnimation.State.Running and hasattr(self, "settings"):
            self.cw, self.ch = self.width(), self.height(); self.chat_rect = self.geometry(); self.layout_body()
    def wheelEvent(self, e): e.ignore()      # розмір вікна міняється трикутником; кружечок — завжди один розмір
    def enterEvent(self, e):
        pass
    def contextMenuEvent(self, e):
        m = QMenu()
        m.addAction(T("Новий чат"), self.new_chat)
        m.addAction(T("Очистити чат"), self.clear_chat)
        m.addAction(T("Видалити чат"), self.delete_chat)
        chats = m.addMenu(T("Чати"))
        for s in self.sessions[:20]:
            mark = "• " if s["id"] == self._chat_id() else ""
            a = chats.addAction(mark + (s.get("title") or "Новий чат")[:42])
            a.triggered.connect(lambda _=False, sid=s["id"]: self.load_chat(sid))
        m.addSeparator()
        m.addAction(T("Пам'ять — павутина"), self.show_memory_web)
        m.addSeparator()
        m.addAction(T("Налаштування"), self.toggle_settings)
        if self.mode == "chat": m.addAction(T("Згорнути в кружечок"), self.collapse)
        else: m.addAction(T("Згорнути / розгорнути"), self.expand)
        m.addSeparator()
        m.addAction(T("Вийти"), self.quit_app)
        m.exec(e.globalPos())
    def quit_app(self):
        self.settings.commit(); self.cfg["chat_w"], self.cfg["chat_h"], self.cfg["orb_size"] = self.cw, self.ch, self.ow
        if self.openlura_server:
            try:self.openlura_server.shutdown(); self.openlura_server.server_close()
            except Exception:pass
        jsave(CFG_P, self.cfg); self._save_chat(); jsave(MEM_P, self.mem); self.server.stop_now(); self.tray.hide(); QApplication.quit()

def main():
    global FONT, EMOJI_SET, EMO_SIG, LANG
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    cfg = load_cfg(); LANG = cfg.get("language", "en") if cfg.get("language") in LANG_NAMES else "en"; cfg["language"] = LANG; FONT = cfg["font"]; EMOJI_SET = cfg["emoji_set"]; EMO_SIG = EmoSig()
    families, local = load_fonts(); set_theme(cfg["theme"])
    want = FONT.strip().casefold()
    installed = next((x for x in families if x.casefold() == want), None) or (local[0] if local else None)   # шрифт з папки поруч — пріоритетний
    if installed: FONT = installed
    app.setFont(ufont(14))
    w = Lura(Bridge()); w.show()
    if QWebEngineView is None:
        QTimer.singleShot(1200, lambda: w.flash_status(T("Для нових анімацій встанови залежності з requirements.txt"), 9000))
    elif not w.face_view:
        QTimer.singleShot(1200, lambda: w.flash_status(T("Не знайшла openlura-engine поруч із програмою"), 9000))
    if not installed:
        w.set_sticky("поклади файл шрифту (.ttf) поруч із lura.py"); QTimer.singleShot(8000, lambda: w.set_sticky(""))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
