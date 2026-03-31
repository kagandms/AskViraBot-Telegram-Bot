import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LocalizationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.locales = {}
            cls._instance.loaded = False
        return cls._instance

    def load_locales(self, locale_dir: str):
        """Load all JSON files from the locale directory."""
        if self.loaded:
            return

        logger.info(f"Loading locales from {locale_dir}...")
        try:
            if not os.path.exists(locale_dir):
                logger.error(f"Locale directory not found: {locale_dir}")
                return

            for filename in os.listdir(locale_dir):
                if filename.endswith(".json"):
                    lang_code = filename.split(".")[0]
                    file_path = os.path.join(locale_dir, filename)
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            self.locales[lang_code] = json.load(f)
                        logger.info(f"Loaded locale: {lang_code}")
                    except Exception as e:
                        logger.error(f"Failed to load locale {filename}: {e}")

            self.loaded = True
        except Exception as e:
            logger.error(f"Error loading locales: {e}")

    def get(self, key: str, lang: str = "en", section: str = "messages") -> str:
        """Get a localized string by key."""
        # 1. Try requested language
        if lang in self.locales and section in self.locales[lang] and key in self.locales[lang][section]:
            return self.locales[lang][section][key]

        # 2. Try English fallback
        if "en" in self.locales and section in self.locales["en"] and key in self.locales["en"][section]:
            return self.locales["en"][section][key]

        # 3. Return key as fallback
        return key

    def get_button(self, key: str, lang: str = "en") -> Any:
        """Get button configuration."""
        return self.get(key, lang, section="buttons")

    def get_all_texts(self) -> dict[str, dict[str, str]]:
        """
        Reconstruct the legacy TEXTS dictionary format:
        { "key": { "tr": "...", "en": "..." } }
        """
        texts = {}
        # Union of all keys across all languages
        all_keys = set()
        for lang_data in self.locales.values():
            if "messages" in lang_data:
                all_keys.update(lang_data["messages"].keys())

        for key in all_keys:
            texts[key] = {}
            for lang in self.locales:
                if "messages" in self.locales[lang] and key in self.locales[lang]["messages"]:
                    texts[key][lang] = self.locales[lang]["messages"][key]

        return texts

    def get_all_buttons(self) -> dict[str, dict[str, Any]]:
        """
        Reconstruct the legacy BUTTONS dictionaries.
        Returns a dict of dicts: { "MAIN_BUTTONS": { "tr": [...], "en": [...] } }
        """
        buttons = {}
        # Identify all button dictionaries (e.g. MAIN_BUTTONS)
        all_dicts = set()
        for lang_data in self.locales.values():
            if "buttons" in lang_data:
                all_dicts.update(lang_data["buttons"].keys())

        for dict_name in all_dicts:
            buttons[dict_name] = {}
            for lang in self.locales:
                if "buttons" in self.locales[lang] and dict_name in self.locales[lang]["buttons"]:
                    buttons[dict_name][lang] = self.locales[lang]["buttons"][dict_name]

        return buttons


# Global instance
i18n = LocalizationManager()
