# utils/inline_keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils import callbacks


def get_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Main Menu Inline Keyboard."""
    t_tools = {"tr": "🧰 Araçlar", "en": "🧰 Tools", "ru": "🧰 Инструменты"}.get(lang, "🧰 Tools")

    t_games = {"tr": "🎮 Oyun Odası", "en": "🎮 Game Room", "ru": "🎮 Игровая Комната"}.get(lang, "🎮 Game Room")

    t_lang = {"tr": "🌐 Dil (Language)", "en": "🌐 Language", "ru": "🌐 Язык"}.get(lang, "🌐 Language")

    t_dev = {"tr": "👨‍💻 Geliştirici", "en": "👨‍💻 Developer", "ru": "👨‍💻 Разработчик"}.get(lang, "👨‍💻 Developer")

    t_ai = {"tr": "🤖 AI Asistan", "en": "🤖 AI Assistant", "ru": "🤖 AI Ассистент"}.get(lang, "🤖 AI Assistant")

    t_help = {"tr": "🆘 Yardım", "en": "🆘 Help", "ru": "🆘 Помощь"}.get(lang, "🆘 Help")

    keyboard = [
        [
            InlineKeyboardButton(t_tools, callback_data=callbacks.MENU_TOOLS),
            InlineKeyboardButton(t_games, callback_data=callbacks.MENU_GAMES),
        ],
        [
            InlineKeyboardButton(t_lang, callback_data=callbacks.MENU_LANGUAGE),
            InlineKeyboardButton(t_dev, callback_data=callbacks.MENU_DEVELOPER),
        ],
        [
            InlineKeyboardButton(t_ai, callback_data=callbacks.MENU_AI),
            InlineKeyboardButton(t_help, callback_data=callbacks.MENU_HELP),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tools_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Tools submenu Inline Keyboard."""
    labels = {
        "tr": {
            "notes": "📝 Notlar",
            "rem": "⏰ Hatırlatıcı",
            "qr": "📷 QR Kod",
            "pdf": "📄 PDF Çevirici",
            "weather": "☀️ Hava Durumu",
            "metro": "🚇 Metro İstanbul",
            "vid": "📥 Video İndir",
            "shazam": "🎵 Shazam",
            "back": "🔙 Ana Menü",
        },
        "en": {
            "notes": "📝 Notes",
            "rem": "⏰ Reminder",
            "qr": "📷 QR Code",
            "pdf": "📄 PDF Converter",
            "weather": "☀️ Weather",
            "metro": "🚇 Metro Istanbul",
            "vid": "📥 Video Downloader",
            "shazam": "🎵 Shazam",
            "back": "🔙 Main Menu",
        },
        "ru": {
            "notes": "📝 Заметки",
            "rem": "⏰ Напоминания",
            "qr": "📷 QR-код",
            "pdf": "📄 PDF Конвертер",
            "weather": "☀️ Погода",
            "metro": "🚇 Метро Стамбул",
            "vid": "📥 Скачать видео",
            "shazam": "🎵 Shazam",
            "back": "🔙 Главное меню",
        },
    }
    lbls = labels.get(lang, labels["en"])

    keyboard = [
        [
            InlineKeyboardButton(lbls["notes"], callback_data=callbacks.TOOL_NOTES),
            InlineKeyboardButton(lbls["rem"], callback_data=callbacks.TOOL_REMINDER),
        ],
        [
            InlineKeyboardButton(lbls["qr"], callback_data=callbacks.TOOL_QR),
            InlineKeyboardButton(lbls["pdf"], callback_data=callbacks.TOOL_PDF),
        ],
        [
            InlineKeyboardButton(lbls["weather"], callback_data=callbacks.TOOL_WEATHER),
            InlineKeyboardButton(lbls["metro"], callback_data=callbacks.TOOL_METRO),
        ],
        [
            InlineKeyboardButton(lbls["vid"], callback_data=callbacks.TOOL_VIDEO),
            InlineKeyboardButton(lbls["shazam"], callback_data=callbacks.TOOL_SHAZAM),
        ],
        [InlineKeyboardButton(lbls["back"], callback_data=callbacks.MENU_MAIN)],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_games_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Games submenu Inline Keyboard."""
    labels = {
        "tr": {
            "xox": "❌⭕ XOX",
            "dice": "🎲 Zar",
            "coin": "🪙 Yazı Tura",
            "tkm": "🪨📄✂️ T-K-M",
            "sudoku": "🧩 Sudoku",
            "snake": "🐍 Yılan",
            "2048": "🔢 2048",
            "flappy": "🐦 Flappy",
            "runner": "🏃 Runner",
            "stats": "📊 İstatistikler",
            "back": "🔙 Ana Menü",
        },
        "en": {
            "xox": "❌⭕ XOX",
            "dice": "🎲 Dice",
            "coin": "🪙 Coinflip",
            "tkm": "🪨📄✂️ R-P-S",
            "sudoku": "🧩 Sudoku",
            "snake": "🐍 Snake",
            "2048": "🔢 2048",
            "flappy": "🐦 Flappy",
            "runner": "🏃 Runner",
            "stats": "📊 Stats",
            "back": "🔙 Main Menu",
        },
        "ru": {
            "xox": "❌⭕ XOX",
            "dice": "🎲 Кубик",
            "coin": "🪙 Монета",
            "tkm": "🪨📄✂️ К-Б-Н",
            "sudoku": "🧩 Судоку",
            "snake": "🐍 Змейка",
            "2048": "🔢 2048",
            "flappy": "🐦 Flappy",
            "runner": "🏃 Runner",
            "stats": "📊 Статистика",
            "back": "🔙 Главное меню",
        },
    }
    lbls = labels.get(lang, labels["en"])

    keyboard = [
        [
            InlineKeyboardButton(lbls["xox"], callback_data=callbacks.GAME_XOX),
            InlineKeyboardButton(lbls["dice"], callback_data=callbacks.GAME_DICE),
        ],
        [
            InlineKeyboardButton(lbls["coin"], callback_data=callbacks.GAME_COINFLIP),
            InlineKeyboardButton(lbls["tkm"], callback_data=callbacks.GAME_TKM),
        ],
        [
            InlineKeyboardButton(lbls["sudoku"], callback_data=callbacks.GAME_SUDOKU),
            InlineKeyboardButton(lbls["snake"], callback_data=callbacks.GAME_SNAKE),
        ],
        [
            InlineKeyboardButton(lbls["2048"], callback_data=callbacks.GAME_2048),
            InlineKeyboardButton(lbls["flappy"], callback_data=callbacks.GAME_FLAPPY),
        ],
        [
            InlineKeyboardButton(lbls["runner"], callback_data=callbacks.GAME_RUNNER),
            InlineKeyboardButton(lbls["stats"], callback_data=callbacks.GAME_STATS),
        ],
        [InlineKeyboardButton(lbls["back"], callback_data=callbacks.MENU_MAIN)],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Returns language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🇹🇷 Türkçe", callback_data=callbacks.LANG_TR)],
        [InlineKeyboardButton("🇬🇧 English", callback_data=callbacks.LANG_EN)],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data=callbacks.LANG_RU)],
        [InlineKeyboardButton("🔙 Back / Geri", callback_data=callbacks.MENU_MAIN)],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(lang: str, target: str) -> InlineKeyboardMarkup:
    """Generic back button to a specific target."""
    text = {"tr": "🔙 Geri", "en": "🔙 Back", "ru": "🔙 Назад"}.get(lang, "🔙 Back")

    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=target)]])


def get_reminder_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Reminder submenu Inline Keyboard."""
    labels = {
        "tr": {"add": "➕ Hatırlatıcı Ekle", "list": "📋 Listele", "del": "🗑️ Sil", "back": "🔙 Araçlar"},
        "en": {"add": "➕ Add Reminder", "list": "📋 List", "del": "🗑️ Delete", "back": "🔙 Tools"},
        "ru": {"add": "➕ Добавить", "list": "📋 Список", "del": "🗑️ Удалить", "back": "🔙 Инструменты"},
    }
    lbls = labels.get(lang, labels["en"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(lbls["add"], callback_data=callbacks.REMINDER_ADD)],
            [InlineKeyboardButton(lbls["list"], callback_data=callbacks.REMINDER_LIST)],
            [InlineKeyboardButton(lbls["del"], callback_data=callbacks.REMINDER_DELETE_MENU)],
            [InlineKeyboardButton(lbls["back"], callback_data=callbacks.TOOL_BACK)],
        ]
    )


def get_notes_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Notes submenu Inline Keyboard."""
    labels = {
        "tr": {
            "add": "➕ Not Ekle",
            "list": "📋 Notları Göster",
            "edit": "✏️ Düzenle",
            "del": "🗑️ Sil",
            "back": "🔙 Araçlar",
        },
        "en": {"add": "➕ Add Note", "list": "📋 Show Notes", "edit": "✏️ Edit", "del": "🗑️ Delete", "back": "🔙 Tools"},
        "ru": {
            "add": "➕ Добавить",
            "list": "📋 Показать",
            "edit": "✏️ Изменить",
            "del": "🗑️ Удалить",
            "back": "🔙 Инструменты",
        },
    }
    lbls = labels.get(lang, labels["en"])

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(lbls["add"], callback_data=callbacks.NOTE_ADD)],
            [InlineKeyboardButton(lbls["list"], callback_data=callbacks.NOTE_LIST)],
            [InlineKeyboardButton(lbls["edit"], callback_data=callbacks.NOTE_EDIT_MENU)],
            [InlineKeyboardButton(lbls["del"], callback_data=callbacks.NOTE_DELETE_MENU)],
            [InlineKeyboardButton(lbls["back"], callback_data=callbacks.TOOL_BACK)],
        ]
    )


def get_metro_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Metro root menu keyboard with Favorites and Back."""
    labels = {
        "tr": {"fav": "⭐ Favorilerim", "back": "🔙 Araçlar"},
        "en": {"fav": "⭐ Favorites", "back": "🔙 Tools"},
        "ru": {"fav": "⭐ Избранное", "back": "🔙 Инструменты"},
    }
    lbls = labels.get(lang, labels["en"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(lbls["fav"], callback_data=callbacks.METRO_FAV_LIST)],
            [InlineKeyboardButton(lbls["back"], callback_data=callbacks.TOOL_BACK)],
        ]
    )


def get_weather_cities_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns inline keyboard with popular cities for weather."""
    cities_en = [
        "Istanbul",
        "Ankara",
        "Kazan",
        "St. Petersburg",
        "Paris",
        "London",
        "Moscow",
        "New York",
        "Berlin",
        "Tokyo",
    ]
    cities_ru = [
        "Стамбул",
        "Анкара",
        "Казань",
        "Санкт-Петербург",
        "Париж",
        "Лондон",
        "Москва",
        "Нью-Йорк",
        "Берлин",
        "Токио",
    ]

    cities = cities_ru if lang == "ru" else cities_en

    keyboard = []
    row = []
    for i, city in enumerate(cities):
        # We still use the english city name for API and callback lookup
        callback_city = cities_en[i]
        row.append(InlineKeyboardButton(city, callback_data=f"WEATHER:CITY:{callback_city}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    back_text = {"tr": "🔙 Araçlar", "en": "🔙 Tools", "ru": "🔙 Инструменты"}.get(lang, "🔙 Tools")
    keyboard.append([InlineKeyboardButton(back_text, callback_data=callbacks.TOOL_BACK)])

    return InlineKeyboardMarkup(keyboard)


def get_pdf_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the PDF converter submenu Inline Keyboard."""
    labels = {
        "tr": {"text": "📝 Metin -> PDF", "img": "🖼️ Resim -> PDF", "doc": "📄 Belge -> PDF", "back": "🔙 Araçlar"},
        "en": {"text": "📝 Text -> PDF", "img": "🖼️ Image -> PDF", "doc": "📄 Doc -> PDF", "back": "🔙 Tools"},
        "ru": {"text": "📝 Текст -> PDF", "img": "🖼️ Изо -> PDF", "doc": "📄 Док -> PDF", "back": "🔙 Инструменты"},
    }
    lbls = labels.get(lang, labels["en"])

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(lbls["text"], callback_data=callbacks.PDF_TEXT)],
            [InlineKeyboardButton(lbls["img"], callback_data=callbacks.PDF_IMAGE)],
            [InlineKeyboardButton(lbls["doc"], callback_data=callbacks.PDF_DOC)],
            [InlineKeyboardButton(lbls["back"], callback_data=callbacks.TOOL_BACK)],
        ]
    )


def get_video_platform_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the Video downloader platform selection keyboard."""
    labels = {"tr": {"back": "🔙 Araçlar"}, "en": {"back": "🔙 Tools"}, "ru": {"back": "🔙 Инструменты"}}
    lbls = labels.get(lang, labels["en"])

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("TikTok", callback_data=callbacks.VIDEO_TIKTOK)],
            [InlineKeyboardButton("Instagram", callback_data=callbacks.VIDEO_INSTAGRAM)],
            [InlineKeyboardButton("Twitter/X", callback_data=callbacks.VIDEO_TWITTER)],
            [InlineKeyboardButton(lbls["back"], callback_data=callbacks.TOOL_BACK)],
        ]
    )


def get_ai_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns the AI chat submenu keyboard."""
    labels = {
        "tr": {"start": "🤖 Sohbeti Başlat", "back": "🔙 Ana Menü"},
        "en": {"start": "🤖 Start Chat", "back": "🔙 Main Menu"},
        "ru": {"start": "🤖 Начать чат", "back": "🔙 Главное меню"},
    }
    lbls = labels.get(lang, labels["en"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(lbls["start"], callback_data=callbacks.AI_START)],
            [InlineKeyboardButton(lbls["back"], callback_data=callbacks.MENU_MAIN)],
        ]
    )


def get_ai_chat_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Returns inline 'End Chat' button to be attached to AI messages."""
    text = {"tr": "🔚 Sohbeti Bitir", "en": "🔚 End Chat", "ru": "🔚 Завершить Чат"}.get(lang, "End Chat")
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callbacks.AI_END)]])
