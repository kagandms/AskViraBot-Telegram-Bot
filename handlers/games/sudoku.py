"""
Sudoku Game Handler
Opens a Telegram Web App for playing Sudoku
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

import database as db
from handlers.games.web_games import get_web_url

logger = logging.getLogger(__name__)


async def sudoku_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Opens Sudoku Web App"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    web_app = WebAppInfo(url=get_web_url("sudoku", lang))
    play_texts = {"tr": "🧩 Sudoku Oyna", "en": "🧩 Play Sudoku", "ru": "🧩 Играть в Sudoku"}
    back_texts = {"tr": "🔙 Oyun Odası", "en": "🔙 Game Room", "ru": "🔙 Игровая Комната"}

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text=play_texts.get(lang, play_texts["en"]), web_app=web_app)],
            [InlineKeyboardButton(text=back_texts.get(lang, back_texts["en"]), callback_data="MENU:GAMES")],
        ]
    )

    prompts = {
        "tr": "🧩 <b>Sudoku</b>\n\nMantik bulmacasi.\n\n1-9 rakamlarini dogru yerlere yerlestir ve tahtayi tamamla.",
        "en": "🧩 <b>Sudoku</b>\n\nClassic logic puzzle.\n\nPlace numbers 1-9 correctly and complete the board.",
        "ru": "🧩 <b>Sudoku</b>\n\nKlassicheskaya logicheskaya golovolomka.\n\nRasstav chisla 1-9 pravilno i zavershi pole.",
    }

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            prompts.get(lang, prompts["en"]), reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await context.bot.send_message(
            chat_id=user_id, text=prompts.get(lang, prompts["en"]), reply_markup=keyboard, parse_mode="HTML"
        )

    logger.info(f"User {user_id} opened Sudoku game")


# --- MODULAR SETUP ---
def setup(app):
    """Register Sudoku handlers"""
    from telegram.ext import CommandHandler

    from core.router import register_button

    # Command
    app.add_handler(CommandHandler("sudoku", sudoku_start))

    # Button registration
    register_button("sudoku_main", sudoku_start)

    logger.info("✅ Sudoku module loaded")
