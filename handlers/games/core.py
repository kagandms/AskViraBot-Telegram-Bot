import asyncio
import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
import state
from rate_limiter import rate_limit
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils import inline_keyboards as kb

logger = logging.getLogger(__name__)

# --- CONSTANTS & HELPERS ---

# Game Names for display
GAME_NAMES = {"tkm": {"tr": "Taş Kağıt Makas", "en": "Rock Paper Scissors", "ru": "Камень Ножницы Бумага"}}


# --- GAMES MENU ---
@rate_limit("games")
async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Oyunlar Alt Menüsünü Açar"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Cleanup previous context
    await cleanup_context(context, user_id)

    text = TEXTS["games_menu_prompt"][lang]
    markup = kb.get_games_keyboard(lang)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text=text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text=text, reply_markup=markup)

    await state.clear_user_states(user_id)


# --- PLAYER STATS ---
@rate_limit("games")
async def show_player_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Oyuncunun oyun istatistiklerini gösterir"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # İstatistikleri çek
    xox_stats = await asyncio.to_thread(db.get_user_xox_stats, user_id)
    tkm_stats = await asyncio.to_thread(db.get_user_tkm_stats, user_id)
    web_stats = await asyncio.to_thread(db.get_web_game_stats, user_id)

    # Başlıklar
    headers = {
        "tr": {
            "title": "📊 *Oyun İstatistikleriniz*",
            "win": "✅ Kazanma",
            "lose": "❌ Kaybetme",
            "draw": "🤝 Berabere",
            "total": "Toplam",
            "highscores": "🏆 *En Yüksek Skorlar*",
        },
        "en": {
            "title": "📊 *Your Game Stats*",
            "win": "✅ Wins",
            "lose": "❌ Losses",
            "draw": "🤝 Draws",
            "total": "Total",
            "highscores": "🏆 *High Scores*",
        },
        "ru": {
            "title": "📊 *Ваша Статистика*",
            "win": "✅ Победы",
            "lose": "❌ Поражения",
            "draw": "🤝 Ничьи",
            "total": "Всего",
            "highscores": "🏆 *Рекорды*",
        },
    }
    h = headers.get(lang, headers["en"])

    def format_stats(name, stats):
        return (
            f"<b>{name}</b>\n"
            f"  {h['win']}: {stats['wins']} | {h['lose']}: {stats['losses']} | {h['draw']}: {stats['draws']}\n"
            f"  {h['total']}: {stats['total']}"
        )

    msg_text = f"{h['title']}\n\n"
    msg_text += f"❌⭕ {format_stats('Legacy XOX', xox_stats)}\n\n"
    msg_text += f"🪨📄✂️ {format_stats('Taş-Kağıt-Makas', tkm_stats)}\n\n"
    msg_text += f"{h['highscores']}\n"
    msg_text += f"🐍 Snake: <b>{web_stats.get('snake', 0)}</b>\n"
    msg_text += f"🔢 2048: <b>{web_stats.get('2048', 0)}</b>\n"
    msg_text += f"🐦 Flappy: <b>{web_stats.get('flappy', 0)}</b>\n"
    msg_text += f"🏃 Runner: <b>{web_stats.get('runner', 0)}</b>\n"
    msg_text += f"🧩 Sudoku: <b>{web_stats.get('sudoku', 0)}</b>\n"
    msg_text += f"❌⭕ XOX (Web): <b>{web_stats.get('xox', 0)}</b>"

    back_kb = kb.get_back_keyboard(lang, callbacks.MENU_GAMES)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(msg_text, reply_markup=back_kb, parse_mode="HTML")
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(msg_text, reply_markup=back_kb, parse_mode="HTML")


# --- DICE & COINFLIP ---
def get_dice_keyboard(lang: str) -> InlineKeyboardMarkup:
    texts = {
        "tr": ["🎲 Tekrar At", "🔙 Oyun Odası"],
        "en": ["🎲 Roll Again", "🔙 Game Room"],
        "ru": ["🎲 Бросить Снова", "🔙 Игровая"],
    }
    t = texts.get(lang, texts["en"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t[0], callback_data="dice_roll")],
            [InlineKeyboardButton(t[1], callback_data=callbacks.MENU_GAMES)],
        ]
    )


def get_coinflip_keyboard(lang: str) -> InlineKeyboardMarkup:
    texts = {
        "tr": ["🪙 Tekrar At", "🔙 Oyun Odası"],
        "en": ["🪙 Flip Again", "🔙 Game Room"],
        "ru": ["🪙 Бросить Снова", "🔙 Игровая"],
    }
    t = texts.get(lang, texts["en"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t[0], callback_data="coinflip_flip")],
            [InlineKeyboardButton(t[1], callback_data=callbacks.MENU_GAMES)],
        ]
    )


@rate_limit("games")
async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    number = random.randint(1, 6)
    await asyncio.to_thread(db.log_dice_roll, user_id, number)

    dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    result_text = f"🎲 {dice_emojis[number]}\n\n{TEXTS['dice_rolled'][lang].format(number=number)}"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(result_text, reply_markup=get_dice_keyboard(lang))
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(result_text, reply_markup=get_dice_keyboard(lang))


@rate_limit("games")
async def coinflip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    result = random.choice(["heads", "tails"])
    await asyncio.to_thread(db.log_coinflip, user_id, result)

    translations = {
        "tr": {"heads": "Yazı", "tails": "Tura"},
        "en": {"heads": "Heads", "tails": "Tails"},
        "ru": {"heads": "Орёл", "tails": "Решка"},
    }
    coin_emoji = "🪙💫" if result == "heads" else "🪙✨"
    result_text = f"{coin_emoji}\n\n{TEXTS['coinflip_result'][lang].format(result=translations[lang][result])}"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(result_text, reply_markup=get_coinflip_keyboard(lang))
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(result_text, reply_markup=get_coinflip_keyboard(lang))


# --- XOX GAME MIGRATED TO WEB APP ---


# --- GLOBAL CALLBACK HANDLER FOR GAMES ---
async def handle_games_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if data == "dice_roll":
        await dice_command(update, context)
    elif data == "coinflip_flip":
        await coinflip_command(update, context)
    elif data == callbacks.GAME_XOX:
        from handlers.games.xox_web import xox_web_start

        await xox_web_start(update, context)
    elif data == callbacks.MENU_GAMES:
        await games_menu(update, context)


# --- MODULAR SETUP ---
def setup(app):
    from telegram.ext import CommandHandler

    from core.router import register_button

    app.add_handler(CommandHandler("games", games_menu))
    app.add_handler(CommandHandler("dice", dice_command))
    app.add_handler(CommandHandler("coinflip", coinflip_command))

    register_button("games_main_button", games_menu)
    register_button("dice", dice_command)
    register_button("coinflip", coinflip_command)

    logger.info("✅ Games module loaded")
