"""
Rock-Paper-Scissors (Taş-Kağıt-Makas) Handler
Converted to Inline Keyboards for premium UX
"""

import asyncio
import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
import state
from rate_limiter import rate_limit
from texts import TEXTS
from utils import cleanup_context

logger = logging.getLogger(__name__)

# --- TEXTS ---
TKM_TEXTS = {
    "welcome": {
        "tr": "🪨📄✂️ <b>Taş-Kağıt-Makas</b>\n\nBir hamle seç:",
        "en": "🪨📄✂️ <b>Rock-Paper-Scissors</b>\n\nChoose your move:",
        "ru": "🪨📄✂️ <b>Камень-Ножницы-Бумага</b>\n\nВыберите ход:",
    },
    "moves": {
        "tr": {"rock": "🪨 Taş", "paper": "📄 Kağıt", "scissors": "✂️ Makas"},
        "en": {"rock": "🪨 Rock", "paper": "📄 Paper", "scissors": "✂️ Scissors"},
        "ru": {"rock": "🪨 Камень", "paper": "📄 Бумага", "scissors": "✂️ Ножницы"},
    },
    "result": {
        "tr": {
            "win": "🎉 <b>Kazandın!</b>\n\n{user} yendi {bot}",
            "lose": "😔 <b>Kaybettin!</b>\n\n{bot} yendi {user}",
            "draw": "🤝 <b>Berabere!</b>\n\nİkiniz de {move} seçti",
        },
        "en": {
            "win": "🎉 <b>You Won!</b>\n\n{user} beats {bot}",
            "lose": "😔 <b>You Lost!</b>\n\n{bot} beats {user}",
            "draw": "🤝 <b>Draw!</b>\n\nBoth chose {move}",
        },
        "ru": {
            "win": "🎉 <b>Ты выиграл(а)!</b>\n\n{user} побеждает {bot}",
            "lose": "😔 <b>Ты проиграл(а)!</b>\n\n{bot} побеждает {user}",
            "draw": "🤝 <b>Ничья!</b>\n\nОба выбрали {move}",
        },
    },
    "play_again": {"tr": "🔄 Tekrar Oyna", "en": "🔄 Play Again", "ru": "🔄 Играть Снова"},
    "back": {"tr": "🔙 Oyun Odası", "en": "🔙 Game Room", "ru": "🔙 Игровая Комната"},
}


def get_tkm_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Generate inline keyboard for TKM game"""
    moves = TKM_TEXTS["moves"][lang]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(moves["rock"], callback_data="tkm_rock"),
                InlineKeyboardButton(moves["paper"], callback_data="tkm_paper"),
                InlineKeyboardButton(moves["scissors"], callback_data="tkm_scissors"),
            ],
            [InlineKeyboardButton(TKM_TEXTS["back"][lang], callback_data="tkm_back")],
        ]
    )


def get_result_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Generate inline keyboard for result screen"""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TKM_TEXTS["play_again"][lang], callback_data="tkm_play_again")],
            [InlineKeyboardButton(TKM_TEXTS["back"][lang], callback_data="tkm_back")],
        ]
    )


def determine_winner(user_move: str, bot_move: str) -> str:
    """Determine the winner: 'win', 'lose', or 'draw'"""
    if user_move == bot_move:
        return "draw"

    wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    return "win" if wins[user_move] == bot_move else "lose"


# --- HANDLERS ---


@rate_limit("games")
async def tkm_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start TKM game with inline keyboard"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    if update.callback_query:
        await update.callback_query.answer()
        sent_msg = await update.callback_query.message.edit_text(
            TKM_TEXTS["welcome"][lang], parse_mode="HTML", reply_markup=get_tkm_keyboard(lang)
        )
        msg_id = getattr(sent_msg, "message_id", update.callback_query.message.message_id)
    else:
        try:
            if update.message:
                await update.message.delete()
        except Exception as e:
            logger.debug(f"TKM start delete error: {e}")
        sent_msg = await update.message.reply_text(
            TKM_TEXTS["welcome"][lang], parse_mode="HTML", reply_markup=get_tkm_keyboard(lang)
        )
        msg_id = sent_msg.message_id

    await state.set_state(user_id, state.PLAYING_TKM, {"message_id": msg_id})


async def handle_tkm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all TKM inline button callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = await db.get_user_lang(user_id)

    await query.answer()

    callback_data = query.data

    # Back to games
    if callback_data == "tkm_back":
        await state.clear_user_states(user_id)
        await query.message.delete()
        from utils import get_games_keyboard_markup

        msg = await context.bot.send_message(
            chat_id=user_id, text=TEXTS["games_menu_prompt"][lang], reply_markup=get_games_keyboard_markup(lang)
        )
        # Save message ID to prevent stacking
        await state.set_state(user_id, state.GAMES_MENU_ACTIVE, {"message_id": msg.message_id})
        return

    # Play again
    if callback_data == "tkm_play_again":
        await query.edit_message_text(
            TKM_TEXTS["welcome"][lang], parse_mode="HTML", reply_markup=get_tkm_keyboard(lang)
        )
        return

    # Game move
    if callback_data.startswith("tkm_"):
        move_map = {"tkm_rock": "rock", "tkm_paper": "paper", "tkm_scissors": "scissors"}
        user_move = move_map.get(callback_data)

        if not user_move:
            return

        # Bot makes random move
        bot_move = random.choice(["rock", "paper", "scissors"])

        # Determine result
        result = determine_winner(user_move, bot_move)

        # Get display names
        moves = TKM_TEXTS["moves"][lang]
        user_display = moves[user_move]
        bot_display = moves[bot_move]

        # Format result message
        if result == "draw":
            result_text = TKM_TEXTS["result"][lang]["draw"].format(move=user_display)
        elif result == "win":
            result_text = TKM_TEXTS["result"][lang]["win"].format(user=user_display, bot=bot_display)
        else:
            result_text = TKM_TEXTS["result"][lang]["lose"].format(user=user_display, bot=bot_display)

        # Log game
        try:
            await asyncio.to_thread(db.log_tkm_game, user_id, user_move, bot_move, result)
        except Exception as e:
            logger.debug(f"TKM log error: {e}")

        # Update message with result
        await query.edit_message_text(result_text, parse_mode="HTML", reply_markup=get_result_keyboard(lang))


# Legacy function for compatibility
async def start_tkm_game(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount: int = 0) -> None:
    """Compatibility wrapper - redirects to inline version"""
    await tkm_start(update, context)


async def tkm_play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy text-based handler - redirects to inline version"""
    # If user types text, redirect to inline keyboard
    await tkm_start(update, context)


# --- MODULAR SETUP ---
def setup(app):
    """Note: TKM is now handled via callbacks, registered in games/__init__.py"""
    from telegram.ext import CallbackQueryHandler

    # Register callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(handle_tkm_callback, pattern=r"^tkm_"))

    logger.info("✅ TKM (Rock-Paper-Scissors) inline module loaded")
