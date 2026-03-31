"""
database.py - Facade for accessing services.
This file maintains backward compatibility by exporting functions from the new service layer.
"""

import logging

# Loglama ayarı (Deprecated usage via this module, but kept for compatibility)
logger = logging.getLogger(__name__)

# --- SERVICES IMPORTS ---

from services.activity_service import log_pdf_usage, log_qr_usage
from services.ai_service import get_ai_daily_usage, get_ai_total_stats, increment_ai_usage, set_ai_daily_usage
from services.game_service import (
    get_user_tkm_stats,
    get_user_xox_stats,
    get_web_game_high_score,  # NEW
    get_web_game_stats,  # NEW
    log_coinflip,
    log_dice_roll,
    log_tkm_game,
    log_xox_game,
    save_web_game_score,  # NEW
)
from services.metro_service import add_metro_favorite, get_metro_favorites, remove_metro_favorite
from services.note_service import (
    add_note,
    add_user_note,
    delete_note,
    delete_user_note_by_id,
    get_all_notes_count,
    get_notes,
    get_user_notes,
    update_note,
    update_user_note,
)
from services.reminder_service import add_reminder_db, get_all_reminders_count, get_all_reminders_db, remove_reminder_db
from services.user_service import (
    clear_user_state,
    get_all_user_ids,
    get_all_users_count,
    get_recent_users,
    get_user_lang,
    get_user_model,
    get_user_state,
    set_user_lang_db,
    set_user_state,
)

# Export explicitly to satisfy linters/static analysis if needed
__all__ = [
    "add_metro_favorite",
    "add_note",
    "add_reminder_db",
    "add_user_note",
    "clear_user_state",
    "delete_note",
    "delete_user_note_by_id",
    "get_ai_daily_usage",
    "get_ai_total_stats",
    "get_all_notes_count",
    "get_all_reminders_count",
    "get_all_reminders_db",
    "get_all_user_ids",
    "get_all_users_count",
    "get_metro_favorites",  # Bunlar eksik?
    "get_notes",
    "get_recent_users",
    "get_user_lang",
    "get_user_model",
    "get_user_notes",
    "get_user_state",
    "get_user_tkm_stats",
    "get_user_xox_stats",
    "get_web_game_high_score",
    "get_web_game_stats",
    "increment_ai_usage",
    "log_coinflip",
    "log_dice_roll",
    "log_pdf_usage",
    "log_qr_usage",
    "log_tkm_game",
    "log_xox_game",
    "remove_metro_favorite",
    "remove_reminder_db",
    "save_web_game_score",
    "set_ai_daily_usage",
    "set_user_lang_db",
    "set_user_state",
    "update_note",
    "update_user_note",
]
