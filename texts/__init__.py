# texts/__init__.py
# Bu dosya geriye dönük uyumluluk için texts modülünden tüm sembolleri export eder

from .common import (
    CITY_NAMES_TRANSLATED,
    SOCIAL_MEDIA_LINKS,
    generate_mappings_from_buttons,
    turkish_lower,
)
from .strings import (
    AUTO_MAPPINGS,
    BET_BUTTONS,
    BUTTON_MAPPINGS,
    DELETE_NOTES_BUTTONS,
    FORMAT_SELECTION_BUTTONS,
    GAME_MODE_BUTTONS,
    GAMES_BUTTONS,
    INPUT_BACK_BUTTONS,
    MAIN_BUTTONS,
    MANUAL_MAPPINGS,
    NOTES_BUTTONS,
    PDF_CONVERTER_BUTTONS,
    REMINDER_BUTTONS,
    TEXTS,
    TKM_BUTTONS,
    TOOLS_BUTTONS,
    VIDEO_DOWNLOADER_BUTTONS,
)

# texts.py'deki tüm sembolleri buradan import edebilirsiniz
# Örnek: from texts import TEXTS, BUTTON_MAPPINGS

__all__ = [
    "AUTO_MAPPINGS",
    "BET_BUTTONS",
    "BUTTON_MAPPINGS",
    "CITY_NAMES_TRANSLATED",
    "DELETE_NOTES_BUTTONS",
    "FORMAT_SELECTION_BUTTONS",
    "GAMES_BUTTONS",
    "GAME_MODE_BUTTONS",
    "INPUT_BACK_BUTTONS",
    "MAIN_BUTTONS",
    "MANUAL_MAPPINGS",
    "NOTES_BUTTONS",
    "PDF_CONVERTER_BUTTONS",
    "REMINDER_BUTTONS",
    "SOCIAL_MEDIA_LINKS",
    "TEXTS",
    "TKM_BUTTONS",
    "TOOLS_BUTTONS",
    "VIDEO_DOWNLOADER_BUTTONS",
    "generate_mappings_from_buttons",
    "turkish_lower",
]
