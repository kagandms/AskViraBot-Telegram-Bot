# handlers/games/__init__.py

import logging

from .core import (
    coinflip_command,
    dice_command,
    games_menu,
    handle_games_callback_router,
    show_player_stats,
)

logger = logging.getLogger(__name__)

import database as db
import state
from texts import TEXTS
from utils import callbacks
from utils import inline_keyboards as kb

from .sudoku import sudoku_start
from .tkm import start_tkm_game, tkm_play, tkm_start
from .web_games import flappy_start, game_2048_start, runner_start, snake_start
from .xox_web import xox_web_start


# --- MODULAR SETUP ---
def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button, router

    # 1. Commands
    app.add_handler(CommandHandler("games", games_menu))
    app.add_handler(CommandHandler("tkm", tkm_start))
    app.add_handler(CommandHandler("xox", xox_web_start))
    app.add_handler(CommandHandler("dice", dice_command))
    app.add_handler(CommandHandler("coinflip", coinflip_command))
    app.add_handler(CommandHandler("stats", show_player_stats))
    app.add_handler(CommandHandler("sudoku", sudoku_start))

    # 2. Router
    router.register(state.PLAYING_TKM, tkm_play)

    # 3. Buttons
    register_button("back_to_games", games_menu)
    register_button("games_main_button", games_menu)
    register_button("xox_game", xox_web_start)
    register_button("dice", dice_command)
    register_button("coinflip", coinflip_command)
    register_button("tkm_main", tkm_start)
    register_button("player_stats", show_player_stats)
    register_button("sudoku_main", sudoku_start)
    register_button("snake_main", snake_start)
    register_button("game_2048_main", game_2048_start)
    register_button("flappy_main", flappy_start)
    register_button("runner_main", runner_start)

    # 4. Callback Query Handlers
    app.add_handler(
        CallbackQueryHandler(handle_games_callback, pattern=r"^(GAME:|dice_roll|coinflip_flip|XOX|tkm_|MENU:GAMES)")
    )

    logger.info("✅ Games module loaded with inline keyboards")


async def handle_games_callback(update, context):
    query = update.callback_query
    data = query.data

    if data == callbacks.MENU_GAMES or data == callbacks.GAME_BACK:
        await games_menu(update, context)
    elif data == callbacks.GAME_XOX:
        await xox_web_start(update, context)
    elif data == callbacks.GAME_DICE:
        await dice_command(update, context)
    elif data == callbacks.GAME_COINFLIP:
        await coinflip_command(update, context)
    elif data == callbacks.GAME_TKM:
        await tkm_start(update, context)
    elif data == callbacks.GAME_SUDOKU:
        await sudoku_start(update, context)
    elif data == callbacks.GAME_SNAKE:
        await snake_start(update, context)
    elif data == callbacks.GAME_2048:
        await game_2048_start(update, context)
    elif data == callbacks.GAME_FLAPPY:
        await flappy_start(update, context)
    elif data == callbacks.GAME_RUNNER:
        await runner_start(update, context)
    elif data == callbacks.GAME_STATS:
        await show_player_stats(update, context)

    # Legacy / Internal
    elif data == "dice_roll":
        await dice_command(update, context)
    elif data == "coinflip_flip":
        await coinflip_command(update, context)
    elif data.startswith("XOX"):
        from .core import handle_xox_game_callback

        await handle_xox_game_callback(update, context)
    elif data.startswith("tkm_"):
        from .tkm import handle_tkm_callback

        await handle_tkm_callback(update, context)
