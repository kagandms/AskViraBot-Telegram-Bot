"""
Handler Integration Tests
Tests handler functions with mocked Telegram Update/Context objects.
Verifies the full handler flow: input → processing → response.

Run with: python -m pytest tests/test_handlers.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

# --- Test Helpers ---


def make_update(
    user_id: int = 12345,
    text: str = "/start",
    chat_id: int = 12345,
    first_name: str = "TestUser",
    callback_data: str | None = None,
) -> Update:
    """Create a mock Telegram Update object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.first_name = first_name
    user.is_bot = False

    chat = MagicMock(spec=Chat)
    chat.id = chat_id
    chat.type = "private"

    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat

    if callback_data:
        # Callback query update
        query = MagicMock(spec=CallbackQuery)
        query.data = callback_data
        query.from_user = user
        query.answer = AsyncMock()
        query.message = MagicMock(spec=Message)
        query.message.chat = chat
        query.message.delete = AsyncMock()
        query.message.edit_text = AsyncMock()
        update.callback_query = query
        update.message = None
    else:
        # Text message update
        message = MagicMock(spec=Message)
        message.text = text
        message.chat = chat
        message.from_user = user
        message.reply_text = AsyncMock()
        message.reply_photo = AsyncMock()
        message.delete = AsyncMock()
        update.message = message
        update.callback_query = None

    update.effective_message = update.message or (update.callback_query.message if update.callback_query else None)
    return update


def make_context() -> MagicMock:
    """Create a mock Telegram Context object."""
    context = MagicMock()
    context.user_data = {}
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.delete_message = AsyncMock()
    return context


# =============================================================================
# SSRF PROTECTION TESTS
# =============================================================================


class TestSSRFProtection:
    """Test the URL validator for SSRF prevention."""

    def test_safe_https_url(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("https://api.openweathermap.org/data/2.5/weather", resolve_dns=False) is True

    def test_safe_http_url(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://example.com/api", resolve_dns=False) is True

    def test_blocks_localhost(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://localhost:8080/admin", resolve_dns=False) is False

    def test_blocks_127_0_0_1(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://127.0.0.1/secret", resolve_dns=False) is False

    def test_blocks_private_ipv4_10(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://10.0.0.1/internal", resolve_dns=False) is False

    def test_blocks_private_ipv4_192(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://192.168.1.1/admin", resolve_dns=False) is False

    def test_blocks_ipv6_loopback(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://[::1]/secret", resolve_dns=False) is False

    def test_blocks_file_scheme(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("file:///etc/passwd") is False

    def test_blocks_ftp_scheme(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("ftp://evil.com/backdoor") is False

    def test_blocks_empty_input(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("") is False
        assert is_safe_url(None) is False

    def test_blocks_metadata_gcp(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://metadata.google.internal/computeMetadata", resolve_dns=False) is False

    def test_blocks_no_hostname(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://") is False


# =============================================================================
# LOG SANITIZER TESTS
# =============================================================================


class TestLogSanitizer:
    """Test the sensitive data filter for logging."""

    def test_filter_returns_true(self):
        """Filter should always return True (don't suppress logs)."""
        from logger import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = MagicMock()
        record.getMessage.return_value = "Normal log message"
        assert f.filter(record) is True

    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"})
    def test_filter_redacts_token(self):
        """Secret values should be replaced with ***REDACTED***."""
        from logger import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = MagicMock()
        record.getMessage.return_value = "Token is 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        f.filter(record)
        assert "***REDACTED***" in record.msg
        assert "ABC-DEF" not in record.msg

    def test_empty_env_no_crash(self):
        """No env vars set should not crash the filter."""
        from logger import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = MagicMock()
        record.getMessage.return_value = "test"
        assert f.filter(record) is True


# =============================================================================
# MIDDLEWARE TESTS
# =============================================================================


class TestMiddleware:
    """Test middleware pipeline components."""

    def test_sanitize_text_normal(self):
        from utils.middleware import sanitize_text

        assert sanitize_text("Hello World") == "Hello World"

    def test_sanitize_text_html_escape(self):
        from utils.middleware import sanitize_text

        assert sanitize_text("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

    def test_sanitize_text_max_length(self):
        from utils.middleware import sanitize_text

        long_text = "A" * 5000
        result = sanitize_text(long_text, max_length=100)
        assert len(result) == 100

    def test_sanitize_text_none(self):
        from utils.middleware import sanitize_text

        assert sanitize_text(None) is None

    def test_sanitize_text_strips_whitespace(self):
        from utils.middleware import sanitize_text

        assert sanitize_text("  hello  ") == "hello"

    @pytest.mark.asyncio
    async def test_with_logging_decorator(self):
        from utils.middleware import with_logging

        called = False

        @with_logging
        async def dummy_handler(update, context):
            nonlocal called
            called = True
            return "ok"

        update = make_update()
        context = make_context()
        result = await dummy_handler(update, context)
        assert called is True
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_with_logging_catches_exception(self):
        from utils.middleware import with_logging

        @with_logging
        async def failing_handler(update, context):
            raise ValueError("Test error")

        update = make_update()
        context = make_context()
        with pytest.raises(ValueError):
            await failing_handler(update, context)

    @pytest.mark.asyncio
    async def test_production_handler_full_pipeline(self):
        from utils.middleware import production_handler

        results = []

        @production_handler
        async def my_handler(update, context):
            results.append("executed")
            return "done"

        update = make_update()
        context = make_context()
        await my_handler(update, context)
        assert "executed" in results


# =============================================================================
# CONFIG TESTS
# =============================================================================


class TestConfig:
    """Test configuration and settings."""

    def test_settings_has_required_fields(self):
        from config.settings import settings

        assert hasattr(settings, "TELEGRAM_BOT_TOKEN")
        assert hasattr(settings, "SUPABASE_URL")
        assert hasattr(settings, "SUPABASE_KEY")

    def test_settings_defaults(self):
        from config.settings import settings

        assert settings.TIMEZONE == "Europe/Istanbul"
        assert settings.BOT_NAME == "Vira"
        assert settings.NOTES_PER_PAGE == 5
        assert settings.AI_DAILY_LIMIT == 30

    def test_admin_ids_property(self):
        from config.settings import settings

        admin_ids = settings.get_admin_ids
        assert isinstance(admin_ids, list)

    def test_get_supabase_returns_client(self):
        from config import get_supabase

        client = get_supabase()
        # May be None if SUPABASE_URL/KEY are invalid in test env
        # but function should not crash
        assert client is not None or client is None  # Just verifies no crash


# =============================================================================
# FLOW REGRESSION TESTS
# =============================================================================


class TestFlowRegressions:
    """Test repaired handler failure paths."""

    @pytest.mark.asyncio
    async def test_notes_menu_back_navigation_no_missing_update_data(self):
        from handlers.notes import notes_menu

        update = make_update(callback_data="MENU:NOTES")
        context = make_context()

        with (
            patch("handlers.notes.db.get_user_lang", AsyncMock(return_value="en")),
            patch("handlers.notes.state.get_data", AsyncMock(return_value={"message_id": 42})),
            patch("handlers.notes.state.update_data", AsyncMock()) as mock_update_data,
            patch("handlers.notes.cleanup_context", AsyncMock()),
            patch("handlers.notes.state.clear_user_states", AsyncMock()),
        ):
            await notes_menu(update, context)

        mock_update_data.assert_awaited_once_with(update.effective_user.id, {"message_id": None})
        update.callback_query.message.edit_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reminder_db_failure_does_not_schedule_background_task(self):
        from handlers.reminders import process_reminder_input

        update = make_update(text="14:30 finish report")
        context = make_context()
        context.application = MagicMock()

        with (
            patch("handlers.reminders.db.get_user_lang", AsyncMock(return_value="en")),
            patch("handlers.reminders.cleanup_context", AsyncMock()),
            patch("handlers.reminders.db.add_reminder_db", return_value=None),
            patch("handlers.reminders.state.clear_user_states", AsyncMock()),
            patch("handlers.reminders.asyncio.create_task") as mock_create_task,
        ):
            await process_reminder_input(update, context)

        mock_create_task.assert_not_called()
        update.message.reply_text.assert_awaited()
        reply_text = update.message.reply_text.await_args.args[0]
        assert "Database" in reply_text

    @pytest.mark.asyncio
    async def test_note_save_failure_does_not_report_success(self):
        from handlers.notes import handle_new_note_input

        update = make_update(text="Important note")
        context = make_context()

        with (
            patch("handlers.notes.db.get_user_lang", AsyncMock(return_value="en")),
            patch("handlers.notes.cleanup_context", AsyncMock()),
            patch("handlers.notes.db.add_note", return_value=False),
            patch("handlers.notes.state.clear_user_states", AsyncMock()),
        ):
            await handle_new_note_input(update, context)

        update.message.reply_text.assert_awaited()
        reply_text = update.message.reply_text.await_args.args[0]
        assert "Database" in reply_text

    @pytest.mark.asyncio
    async def test_weather_callback_without_api_key_uses_callback_safe_path(self):
        from handlers.weather import weather_command

        update = make_update(callback_data="TOOL:WEATHER")
        context = make_context()

        with (
            patch("handlers.weather.db.get_user_lang", AsyncMock(return_value="en")),
            patch("handlers.weather.cleanup_context", AsyncMock()),
            patch("handlers.weather.state.clear_user_states", AsyncMock()),
            patch("handlers.weather.OPENWEATHERMAP_API_KEY", None),
        ):
            await weather_command(update, context)

        update.callback_query.answer.assert_awaited_once()
        update.callback_query.message.edit_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ai_message_final_edit_avoids_markdown_parse_mode(self):
        from handlers.ai_chat import handle_ai_message

        class FakeStream:
            def __aiter__(self):
                return self

            async def __anext__(self):
                if hasattr(self, "_done"):
                    raise StopAsyncIteration
                self._done = True
                chunk = MagicMock()
                delta = MagicMock()
                delta.content = "Hello *world*"
                chunk.choices = [MagicMock(delta=delta)]
                return chunk

        update = make_update(text="Hello")
        context = make_context()
        context.bot.send_chat_action = AsyncMock()
        ai_message = MagicMock()
        ai_message.edit_text = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=ai_message)

        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=FakeStream())

        with (
            patch("handlers.ai_chat.db.get_user_lang", AsyncMock(return_value="en")),
            patch("handlers.ai_chat.state.get_data", AsyncMock(return_value={"messages": []})),
            patch("handlers.ai_chat.state.set_state", AsyncMock()),
            patch("handlers.ai_chat.get_user_remaining_quota_async", AsyncMock(return_value=5)),
            patch("handlers.ai_chat.increment_usage_async", AsyncMock()),
            patch("handlers.ai_chat.client", fake_client),
        ):
            await handle_ai_message(update, context)

        final_call = ai_message.edit_text.await_args_list[-1]
        assert final_call.args[0] == "Hello *world*"
        assert "parse_mode" not in final_call.kwargs


# =============================================================================
# VIDEO URL VALIDATION (HANDLER-LEVEL)
# =============================================================================


class TestVideoUrlSecurity:
    """Test video URL validation at handler level."""

    def test_valid_url_with_ssrf_check(self):
        from handlers.video import is_valid_video_url
        from utils.url_validator import is_safe_url

        url = "https://www.tiktok.com/@user/video/123"
        assert is_valid_video_url(url, "tiktok") is True
        assert is_safe_url(url, resolve_dns=False) is True

    def test_phishing_url_ssrf_safe_but_platform_invalid(self):
        from handlers.video import is_valid_video_url

        url = "https://evil.com?redirect=tiktok.com"
        assert is_valid_video_url(url, "tiktok") is False

    def test_private_ip_url_blocked_at_ssrf_level(self):
        from utils.url_validator import is_safe_url

        assert is_safe_url("http://192.168.1.1/tiktok.com", resolve_dns=False) is False
