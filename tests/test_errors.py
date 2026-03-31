"""
Error Messages Unit Tests
Tests for get_error_message, log_error_with_context,
and ERROR_MESSAGES data consistency.

Run with: python -m pytest tests/test_errors.py -v
"""

import logging
from unittest.mock import MagicMock


class TestErrorMessagesData:
    """Test ERROR_MESSAGES dictionary consistency."""

    def test_all_messages_have_three_languages(self):
        """Every error type must have tr, en, ru translations."""
        from errors import ERROR_MESSAGES

        for key, translations in ERROR_MESSAGES.items():
            assert "tr" in translations, f"{key} missing Turkish"
            assert "en" in translations, f"{key} missing English"
            assert "ru" in translations, f"{key} missing Russian"

    def test_all_messages_are_nonempty_strings(self):
        """Every translation must be a non-empty string."""
        from errors import ERROR_MESSAGES

        for key, translations in ERROR_MESSAGES.items():
            for lang, text in translations.items():
                assert isinstance(text, str), f"{key}[{lang}] is not a string"
                assert len(text) > 0, f"{key}[{lang}] is empty"

    def test_required_error_types_exist(self):
        """Critical error types must be defined."""
        from errors import ERROR_MESSAGES

        required = [
            "generic_error",
            "network_error",
            "timeout_error",
            "api_error",
            "permission_denied",
            "invalid_input",
            "rate_limited",
            "database_error",
        ]
        for error_type in required:
            assert error_type in ERROR_MESSAGES, f"Missing: {error_type}"

    def test_rate_limited_has_format_placeholder(self):
        """rate_limited message must contain {seconds} placeholder."""
        from errors import ERROR_MESSAGES

        for lang in ["tr", "en", "ru"]:
            assert "{seconds}" in ERROR_MESSAGES["rate_limited"][lang], (
                f"rate_limited[{lang}] missing {{seconds}} placeholder"
            )


class TestGetErrorMessage:
    """Test get_error_message function."""

    def test_valid_error_type_returns_correct_language(self):
        """Should return message in the requested language."""
        from errors import get_error_message

        msg_tr = get_error_message("generic_error", "tr")
        msg_en = get_error_message("generic_error", "en")
        msg_ru = get_error_message("generic_error", "ru")
        assert "hata" in msg_tr.lower() or "⚠️" in msg_tr
        assert "error" in msg_en.lower() or "⚠️" in msg_en
        assert "ошибка" in msg_ru.lower() or "⚠️" in msg_ru

    def test_unknown_error_type_falls_back_to_generic(self):
        """Unknown error type should return generic_error."""
        from errors import ERROR_MESSAGES, get_error_message

        result = get_error_message("nonexistent_error_type", "en")
        expected = ERROR_MESSAGES["generic_error"]["en"]
        assert result == expected

    def test_unknown_language_falls_back_to_english(self):
        """Unknown language should fall back to English."""
        from errors import ERROR_MESSAGES, get_error_message

        result = get_error_message("generic_error", "jp")
        expected = ERROR_MESSAGES["generic_error"]["en"]
        assert result == expected

    def test_format_kwargs_applied(self):
        """Format parameters should be applied to the message."""
        from errors import get_error_message

        msg = get_error_message("rate_limited", "en", seconds=30)
        assert "30" in msg

    def test_format_kwargs_invalid_key_no_crash(self):
        """Invalid format kwargs should not crash."""
        from errors import get_error_message

        # generic_error has no placeholders, extra kwargs should be ignored
        msg = get_error_message("generic_error", "en", invalid_key="value")
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_default_language_is_english(self):
        """Default language parameter should be English."""
        from errors import ERROR_MESSAGES, get_error_message

        msg = get_error_message("generic_error")
        assert msg == ERROR_MESSAGES["generic_error"]["en"]


class TestLogErrorWithContext:
    """Test log_error_with_context function."""

    def test_logs_error_with_all_fields(self):
        """Should log error with user_id, handler, and action."""
        from errors import log_error_with_context

        mock_logger = MagicMock(spec=logging.Logger)
        error = ValueError("test error")
        context = {"user_id": 12345, "handler": "pdf_handler", "action": "convert_pdf"}
        log_error_with_context(mock_logger, error, context)
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "12345" in call_args
        assert "pdf_handler" in call_args
        assert "convert_pdf" in call_args
        assert "ValueError" in call_args

    def test_missing_context_fields_use_defaults(self):
        """Missing context fields should use 'unknown' default."""
        from errors import log_error_with_context

        mock_logger = MagicMock(spec=logging.Logger)
        error = RuntimeError("test")
        log_error_with_context(mock_logger, error, {})
        call_args = mock_logger.error.call_args[0][0]
        assert "unknown" in call_args
