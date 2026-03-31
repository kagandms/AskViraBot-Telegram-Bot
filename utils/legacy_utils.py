import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from config import ADMIN_IDS

# TOOLS_BUTTONS eklendi
from texts import (
    CITY_NAMES_TRANSLATED,
    DELETE_NOTES_BUTTONS,
    GAMES_BUTTONS,
    INPUT_BACK_BUTTONS,
    MAIN_BUTTONS,
    NOTES_BUTTONS,
    PDF_CONVERTER_BUTTONS,
    REMINDER_BUTTONS,
    SOCIAL_MEDIA_LINKS,
    TEXTS,
    TOOLS_BUTTONS,
)

# Import shared utilities from helpers.py to avoid duplication (DRY principle)

logger = logging.getLogger(__name__)

# --- KLAVYE OLUŞTURUCULAR ---


def get_main_keyboard_markup(lang: str, user_id: int | None = None) -> ReplyKeyboardMarkup:
    # Ana menü klavyesi
    buttons = [row[:] for row in MAIN_BUTTONS.get(lang, MAIN_BUTTONS["en"])]  # Deep copy

    # Admin kullanıcıya özel buton ekle
    if user_id and user_id in ADMIN_IDS:
        admin_button = {"tr": "🔒 Yönetim", "en": "🔒 Admin", "ru": "🔒 Управление"}
        buttons.append([admin_button.get(lang, admin_button["en"])])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_games_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    # Oyunlar menüsü klavyesi (YENİ EKLENEN)
    buttons = GAMES_BUTTONS.get(lang, GAMES_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_notes_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    # Notlar menüsü klavyesi
    buttons = NOTES_BUTTONS.get(lang, NOTES_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_tools_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    # Araçlar menüsü klavyesi
    buttons = TOOLS_BUTTONS.get(lang, TOOLS_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_delete_notes_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    buttons = DELETE_NOTES_BUTTONS.get(lang, DELETE_NOTES_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_input_back_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    buttons = INPUT_BACK_BUTTONS.get(lang, INPUT_BACK_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_pdf_converter_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    buttons = PDF_CONVERTER_BUTTONS.get(lang, PDF_CONVERTER_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_social_media_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(TEXTS["my_website"][lang], url=SOCIAL_MEDIA_LINKS["website"])],
        [InlineKeyboardButton("📸 Instagram", url=SOCIAL_MEDIA_LINKS["instagram"])],
        [InlineKeyboardButton("✈️ Telegram", url=SOCIAL_MEDIA_LINKS["telegram"])],
        [InlineKeyboardButton("👔 LinkedIn", url=SOCIAL_MEDIA_LINKS["linkedin"])],
        [InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data="back_to_main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reminder_keyboard_markup(lang: str) -> ReplyKeyboardMarkup:
    buttons = REMINDER_BUTTONS.get(lang, REMINDER_BUTTONS["en"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_weather_cities_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # Hava durumu şehir seçimi için Reply Keyboard
    cities_dict = CITY_NAMES_TRANSLATED.get(lang, CITY_NAMES_TRANSLATED["en"])
    # Dictionary values (şehir isimleri) alınıyor
    city_names = list(cities_dict.values())

    # 2'li satırlar halinde düzenle
    keyboard = []
    row = []
    for city in city_names:
        row.append(city)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Geri butonu - Araçlar menüsüne döner
    back_texts = {"tr": "🔙 Araçlar Menüsü", "en": "🔙 Tools Menu", "ru": "🔙 Меню Инструментов"}
    back_text = back_texts.get(lang, back_texts["en"])
    keyboard.append([back_text])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# NOTE: is_back_button, format_remaining_time, cleanup_context,
# send_temp_message, delete_user_message are now imported from utils.helpers
# to follow DRY principle. See imports at the top of this file.
