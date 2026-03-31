import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import settings

logger = logging.getLogger(__name__)


def attach_user(func):
    """
    Decorator that attaches the user model to the function arguments.
    Usage:
        @attach_user
        async def my_handler(update, context, user):

    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        # Explicitly fetch user model using new Pydantic method
        user = db.get_user_model(user_id)

        # Inject 'user' into kwargs if not present
        if "user" not in kwargs:
            kwargs["user"] = user

        return await func(update, context, *args, **kwargs)

    return wrapper


def handle_errors(func):
    """
    Decorator to wrap handlers with a standardized try/except block.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            # Manually inject error into context so global handler logic is mimicked
            context.error = e
            from utils.errors import global_error_handler

            await global_error_handler(update, context)

    return wrapper


def admin_only(func):
    """
    Decorator to restrict handler access to admin users only.
    Provides centralized admin authorization check.
    Usage:
        @admin_only
        async def my_admin_handler(update, context):
            ...
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        admin_ids = settings.get_admin_ids
        if user_id not in admin_ids:
            await update.message.reply_text("⛔ Bu komuta erişim yetkiniz yok.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
