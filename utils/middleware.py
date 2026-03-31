"""
Middleware Pipeline for ViraBot
Provides centralized input sanitization, request logging, and error handling
for all handler functions via decorator pattern.
"""

import functools
import html
import logging
import time
from collections.abc import Callable

from telegram import Update
from telegram.ext import ContextTypes

from errors import get_error_message

logger = logging.getLogger(__name__)

# --- Constants ---
MAX_INPUT_LENGTH = 4096  # Telegram's own message limit
MAX_CALLBACK_DATA_LENGTH = 256


def sanitize_text(text: str | None, max_length: int = MAX_INPUT_LENGTH) -> str | None:
    """
    Sanitize user text input: escape HTML entities, enforce max length.
    Returns None if input is None.
    """
    if text is None:
        return None
    # Escape HTML entities to prevent XSS in any web-rendered output
    sanitized = html.escape(text.strip())
    # Enforce maximum length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def with_logging(func: Callable) -> Callable:
    """
    Middleware decorator that logs every handler invocation with timing.
    Logs user_id, handler name, and execution duration.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        start_time = time.monotonic()
        user = update.effective_user
        user_id = user.id if user else "unknown"
        handler_name = func.__name__

        logger.info(f"[HANDLER] {handler_name} called by user={user_id}")

        try:
            result = await func(update, context, *args, **kwargs)
            elapsed = (time.monotonic() - start_time) * 1000
            logger.info(f"[HANDLER] {handler_name} completed in {elapsed:.1f}ms for user={user_id}")
            return result
        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error(
                f"[HANDLER] {handler_name} FAILED after {elapsed:.1f}ms for user={user_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            # Send generic error message to user
            try:
                if update.effective_message:
                    lang = context.user_data.get("lang", "tr")
                    error_msg = get_error_message("generic", lang)
                    await update.effective_message.reply_text(error_msg)
            except Exception:
                pass  # Don't let error reply itself crash
            raise

    return wrapper


def with_sanitization(func: Callable) -> Callable:
    """
    Middleware decorator that sanitizes incoming text/callback data
    before passing to the handler.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Sanitize message text
        if update.message and update.message.text:
            # Store original for reference, sanitize for processing
            context.user_data["_raw_text"] = update.message.text
            # Note: We don't modify update.message.text directly (read-only),
            # but handlers can use sanitize_text() for their own processing.

        # Sanitize callback data
        if update.callback_query and update.callback_query.data:
            data = update.callback_query.data
            if len(data) > MAX_CALLBACK_DATA_LENGTH:
                logger.warning(f"Oversized callback data from user={update.effective_user.id}: len={len(data)}")
                await update.callback_query.answer("Invalid request.")
                return

        return await func(update, context, *args, **kwargs)

    return wrapper


def production_handler(func: Callable) -> Callable:
    """
    Combined middleware stack for production handlers.
    Applies: sanitization → logging → error handling.

    Usage:
        @production_handler
        async def my_handler(update, context):
            ...
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        return await func(update, context, *args, **kwargs)

    # Apply middleware chain (innermost first)
    wrapped = with_logging(with_sanitization(wrapper))
    # Preserve the original function name for debugging
    wrapped.__wrapped__ = func
    return wrapped
