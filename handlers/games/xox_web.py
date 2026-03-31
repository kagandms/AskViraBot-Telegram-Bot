"""
XOX (Tic-Tac-Toe) Web Game Handler
Opens a Telegram Web App for playing XOX
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

import database as db
from handlers.games.web_games import get_web_url

logger = logging.getLogger(__name__)


async def xox_web_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Opens XOX Web App"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    xox_url = get_web_url("xox", lang)

    # Create Web App button with back button
    web_app = WebAppInfo(url=xox_url)
    play_texts = {"tr": "❌⭕ XOX Oyna", "en": "❌⭕ Play XOX", "ru": "❌⭕ Играть в XOX"}
    back_texts = {"tr": "🔙 Oyun Odası", "en": "🔙 Game Room", "ru": "🔙 Игровая Комната"}

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text=play_texts.get(lang, play_texts["en"]), web_app=web_app)],
            [InlineKeyboardButton(text=back_texts.get(lang, back_texts["en"]), callback_data="MENU:GAMES")],
        ]
    )

    prompts = {
        "tr": "❌⭕ *XOX (Tic-Tac-Toe)*\n\nKlasik XOX oyunu!\n\n🎯 *Zorluk Seviyeleri:*\n• 🟢 Kolay - Rahat kazanabilirsin\n• 🟡 Orta - Dikkatli ol\n• 🔴 Zor - Yenilmez bot!\n\n📊 Skor takibi ve harika animasyonlar!",
        "en": "❌⭕ *XOX (Tic-Tac-Toe)*\n\nClassic XOX game!\n\n🎯 *Difficulty Levels:*\n• 🟢 Easy - You can win easily\n• 🟡 Medium - Be careful\n• 🔴 Hard - Unbeatable bot!\n\n📊 Score tracking and awesome animations!",
        "ru": "❌⭕ *XOX (Крестики-нолики)*\n\nКлассическая игра XOX!\n\n🎯 *Уровни сложности:*\n• 🟢 Лёгкий - Легко победить\n• 🟡 Средний - Будь осторожен\n• 🔴 Сложный - Непобедимый бот!\n\n📊 Счёт и красивые анимации!",
    }

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text=prompts.get(lang, prompts["en"]), reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        try:
            if update.message:
                await update.message.delete()
        except Exception as e:
            logger.debug(f"Failed to delete message in xox_web_start: {e}")

        await context.bot.send_message(
            chat_id=user_id, text=prompts.get(lang, prompts["en"]), reply_markup=keyboard, parse_mode="HTML"
        )

    logger.info(f"User {user_id} opened XOX web game")
