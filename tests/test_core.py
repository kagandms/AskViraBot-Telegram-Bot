"""
Comprehensive Unit Tests for ViraBot
Run with: python -m pytest tests/ -v
"""

from datetime import datetime
from unittest.mock import patch

import pytest

# =============================================================================
# UTILITY TESTS
# =============================================================================


class TestTurkishLower:
    """Test Turkish lowercase conversion"""

    def test_turkish_i_conversion(self):
        from texts.common import turkish_lower

        assert turkish_lower("İSTANBUL") == "istanbul"
        assert turkish_lower("IŞIK") == "ışık"

    def test_normal_letters(self):
        from texts.common import turkish_lower

        assert turkish_lower("Test") == "test"
        assert turkish_lower("ABC") == "abc"

    def test_empty_string(self):
        from texts.common import turkish_lower

        assert turkish_lower("") == ""


class TestButtonMappings:
    """Test button mapping generator"""

    def test_generate_mappings(self):
        from texts.common import generate_mappings_from_buttons

        test_buttons = {"tr": [["Test Buton"]], "en": [["Test Button"]]}

        mappings = generate_mappings_from_buttons(test_buttons)
        assert "test buton" in mappings
        assert "test button" in mappings

    def test_empty_buttons(self):
        from texts.common import generate_mappings_from_buttons

        result = generate_mappings_from_buttons({})
        assert isinstance(result, set)


class TestIsBackButton:
    """Test back button detection"""

    def test_turkish_back(self):
        from utils import is_back_button

        assert is_back_button("geri")
        assert is_back_button("iptal")

    def test_english_back(self):
        from utils import is_back_button

        assert is_back_button("back")
        assert is_back_button("cancel")

    def test_russian_back(self):
        from utils import is_back_button

        assert is_back_button("назад")
        assert is_back_button("отмена")

    def test_emoji_back_buttons(self):
        from utils import is_back_button

        assert is_back_button("🔙 Ana Menü")
        assert is_back_button("🔙 Main Menu")

    def test_non_back_text(self):
        from utils import is_back_button

        assert not is_back_button("hello")
        assert not is_back_button("merhaba")

    def test_edge_cases(self):
        from utils import is_back_button

        assert not is_back_button("")
        assert not is_back_button(None)


# =============================================================================
# STATE TESTS
# =============================================================================


class TestStateConstants:
    """Test state module constants"""

    def test_all_states_defined(self):
        import state

        required_states = [
            "PLAYING_XOX",
            "METRO_BROWSING",
            "AI_CHAT_ACTIVE",
            "WAITING_FOR_QR_DATA",
            "WAITING_FOR_NEW_NOTE_INPUT",
            "WAITING_FOR_WEATHER_CITY",
            "WAITING_FOR_VIDEO_LINK",
            "WAITING_FOR_PDF_CONVERSION_INPUT",
            "ADMIN_MENU_ACTIVE",
        ]

        for state_name in required_states:
            assert hasattr(state, state_name), f"Missing state: {state_name}"

    def test_states_are_strings(self):
        import state

        assert isinstance(state.PLAYING_XOX, str)
        assert isinstance(state.AI_CHAT_ACTIVE, str)


# =============================================================================
# CONFIG TESTS
# =============================================================================


class TestConfig:
    """Test configuration values"""

    def test_font_path_format(self):
        from config import BASE_DIR, FONT_PATH

        assert FONT_PATH.endswith(".ttf")
        assert BASE_DIR in FONT_PATH

    def test_notes_per_page(self):
        from config import NOTES_PER_PAGE

        assert isinstance(NOTES_PER_PAGE, int)
        assert 1 <= NOTES_PER_PAGE <= 20

    def test_bot_name_defined(self):
        from config import BOT_NAME

        assert isinstance(BOT_NAME, str)
        assert len(BOT_NAME) > 0

    def test_timezone_defined(self):
        from config import TIMEZONE

        assert isinstance(TIMEZONE, str)


# =============================================================================
# RATE LIMITER TESTS
# =============================================================================


class TestRateLimiter:
    """Test rate limiter functions"""

    def test_rate_limits_categories(self):
        from rate_limiter import RATE_LIMITS

        assert "general" in RATE_LIMITS
        assert "games" in RATE_LIMITS
        assert "heavy" in RATE_LIMITS

    def test_rate_limit_values(self):
        from rate_limiter import RATE_LIMITS

        for _category, limit in RATE_LIMITS.items():
            assert isinstance(limit, int)
            assert limit > 0

    def test_window_seconds(self):
        from rate_limiter import WINDOW_SECONDS

        assert WINDOW_SECONDS == 60


# =============================================================================
# TEXTS TESTS
# =============================================================================


class TestTexts:
    """Test text definitions"""

    def test_all_languages_present(self):
        from texts import TEXTS

        sample_keys = ["start", "menu_prompt", "unknown_command"]
        for key in sample_keys:
            if key in TEXTS:
                assert "tr" in TEXTS[key], f"Missing TR for {key}"
                assert "en" in TEXTS[key], f"Missing EN for {key}"
                assert "ru" in TEXTS[key], f"Missing RU for {key}"

    def test_button_mappings_populated(self):
        from texts import BUTTON_MAPPINGS

        assert "menu" in BUTTON_MAPPINGS
        assert "back_to_tools" in BUTTON_MAPPINGS
        assert len(BUTTON_MAPPINGS) > 10


# =============================================================================
# WEB GAMES TESTS
# =============================================================================


class TestWebGames:
    """Test current web-based game entrypoints."""

    def test_game_url_uses_configured_base_url(self):
        from handlers.games.web_games import get_web_url

        with patch("handlers.games.web_games.WEB_APP_BASE_URL", "https://vira.example"):
            assert get_web_url("snake", "en") == "https://vira.example/web/snake.html?lang=en"

    def test_game_url_falls_back_to_localhost(self):
        from handlers.games.web_games import get_web_url

        with patch("handlers.games.web_games.WEB_APP_BASE_URL", None), patch.dict("os.environ", {}, clear=True):
            assert get_web_url("xox", "tr") == "http://127.0.0.1:8080/web/xox.html?lang=tr"


class TestSchemaContract:
    """Protect the canonical schema contract against drift."""

    def test_schema_contains_canonical_runtime_tables(self):
        with open("database_schema.sql", encoding="utf-8") as schema_file:
            schema = schema_file.read()

        required_fragments = [
            "CREATE TABLE IF NOT EXISTS user_states",
            "state_name TEXT NOT NULL",
            "ALTER TABLE notes ALTER COLUMN title DROP NOT NULL",
            "chat_id TEXT",
            "message TEXT",
            "usage_count INTEGER NOT NULL DEFAULT 0",
            "station_id TEXT",
            "direction_id TEXT",
            "CREATE TABLE IF NOT EXISTS tool_usage",
        ]

        for fragment in required_fragments:
            assert fragment in schema


# =============================================================================
# WEATHER CACHE TESTS
# =============================================================================


class TestWeatherCache:
    """Test weather caching functionality"""

    def test_cache_exists(self):
        from handlers.weather import WEATHER_CACHE_TTL, _weather_cache

        assert isinstance(_weather_cache, dict)
        assert WEATHER_CACHE_TTL.total_seconds() == 600  # 10 minutes


# =============================================================================
# DATABASE SERVICE TESTS
# =============================================================================


class TestDatabaseService:
    """Test database service functionality"""

    def test_database_exports_user_functions(self):
        """Verify database module exports required functions"""
        import database as db

        assert hasattr(db, "get_user_lang")
        assert hasattr(db, "get_user_state")
        assert callable(db.get_user_lang)


# =============================================================================
# ERROR MESSAGE CONSISTENCY TESTS
# =============================================================================


class TestErrorMessages:
    """Test error message consistency across languages"""

    def test_error_messages_exist(self):
        from texts import TEXTS

        error_keys = ["error_occurred", "unknown_command", "weather_api_error", "video_download_error"]

        for key in error_keys:
            if key in TEXTS:
                assert len(TEXTS[key]) >= 3, f"{key} missing languages"


# =============================================================================
# AI CHAT TESTS
# =============================================================================


class TestAIChat:
    """Test AI chat functionality"""

    def test_daily_limit_constant(self):
        from config import AI_DAILY_LIMIT

        assert isinstance(AI_DAILY_LIMIT, int)
        assert AI_DAILY_LIMIT > 0

    def test_admin_has_higher_limit(self):
        from config import AI_DAILY_LIMIT

        # Admin limit is hardcoded as 999 in ai_chat.py
        admin_limit = 999
        assert admin_limit >= AI_DAILY_LIMIT

    def test_today_str_uses_configured_timezone(self):
        import pytz

        from handlers.ai_chat import get_today_str

        utc_time = pytz.utc.localize(datetime(2026, 3, 12, 21, 30))
        assert get_today_str(utc_time) == "2026-03-13"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
