"""
Centralized Logging Configuration for ViraBot
Provides consistent logging across all modules.
Includes sensitive data filtering to prevent secret leakage.
"""

import logging
import os
import re
from logging.handlers import RotatingFileHandler

# Log level from environment (default: INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Create formatter
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(LOG_FORMAT)


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that redacts sensitive data (API keys, tokens, passwords)
    from log messages to prevent credential leakage in production.
    """

    def __init__(self) -> None:
        super().__init__()
        self._patterns: list[re.Pattern] = []
        self._build_patterns()

    def _build_patterns(self) -> None:
        """Build regex patterns from environment secrets."""
        secret_env_keys = [
            "TELEGRAM_BOT_TOKEN",
            "SUPABASE_KEY",
            "OPENROUTER_API_KEY",
            "OPENWEATHERMAP_API_KEY",
            "REDIS_URL",
        ]
        for key in secret_env_keys:
            value = os.getenv(key, "")
            if value and len(value) > 8:
                # Escape special regex characters in the secret value
                escaped = re.escape(value)
                self._patterns.append(re.compile(escaped))

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive values from the log record message."""
        if self._patterns:
            msg = record.getMessage()
            for pattern in self._patterns:
                msg = pattern.sub("***REDACTED***", msg)
            record.msg = msg
            record.args = None  # Clear args to prevent re-formatting
        return True


# Configure root logger
def setup_logging() -> logging.Logger:
    """Configure logging for the entire application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Add sensitive data filter FIRST (before any handlers)
    sensitive_filter = SensitiveDataFilter()
    root_logger.addFilter(sensitive_filter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Avoid duplicate handlers
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    # Optional: File handler (can be enabled via environment variable)
    if os.getenv("LOG_TO_FILE", "false").lower() == "true":
        log_file = os.getenv("LOG_FILE_PATH", "virabot.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(name)
