import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db

logger = logging.getLogger(__name__)


class BotError(Exception):
    """Base exception for bot-related errors that should be shown to the user."""

    def __init__(self, message_key: str, **kwargs):
        self.message_key = message_key
        self.kwargs = kwargs
        super().__init__(self.message_key)


async def global_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if not update:
        return

    user_id = update.effective_user.id if update.effective_user else None

    # Varsayılan hata mesajı
    # (İleri seviyede burayı db.get_user_lang ile kişiselleştirebiliriz)
    if update.effective_message:
        try:
            lang = "en"
            if user_id:
                try:
                    # Hata anında DB erişimi riskli olabilir ama denemeye değer
                    lang = await db.get_user_lang(user_id)  # async wrapper gerekebilir
                    if asyncio.iscoroutine(lang):
                        lang = await lang
                except:
                    pass

            error_text = "⚠️ An error occurred. Please try again later."
            if lang == "tr":
                error_text = "⚠️ Bir hata oluştu. Lütfen daha sonra tekrar deneyin."
            elif lang == "ru":
                error_text = "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."

            # Eğer özel bir BotError ise daha anlamlı mesaj göster
            if isinstance(context.error, BotError):
                # Burada localization'dan key ile mesaj çekilebilir
                # Şimdilik generic bırakıyoruz
                pass

            await update.effective_message.reply_text(error_text)
        except Exception:
            pass
