import asyncio

import database as db

# --- STATE CONSTANTS (Durum Sabitleri) ---
PLAYING_TKM = "playing_tkm"
NOTES_IN_MENU = "notes_in_menu"
DELETING_NOTES = "deleting_notes"
WAITING_FOR_QR_DATA = "waiting_for_qr_data"
WAITING_FOR_REMINDER_INPUT = "waiting_for_reminder_input"
WAITING_FOR_PDF_CONVERSION_INPUT = "waiting_for_pdf_conversion_input"
WAITING_FOR_WEATHER_CITY = "waiting_for_weather_city"
REMINDER_MENU_ACTIVE = "reminder_menu_active"
WAITING_FOR_REMINDER_DELETE = "waiting_for_reminder_delete"
WAITING_FOR_NEW_NOTE_INPUT = "waiting_for_new_note_input"
WAITING_FOR_EDIT_NOTE_INPUT = "waiting_for_edit_note_input"  # Data: note_id
EDITING_NOTES = "editing_notes"
GAMES_MENU_ACTIVE = "games_menu_active"
PLAYING_XOX = "playing_xox"  # Data: Game state
WAITING_FOR_SHAZAM = "waiting_for_shazam"  # Data: none
# Vira: Gambling states removed (PLAYING_BLACKJACK, WAITING_FOR_BJ_BET, WAITING_FOR_SLOT_BET, PLAYING_SLOT, WAITING_FOR_GAME_MODE, WAITING_FOR_TKM_BET)
WAITING_FOR_VIDEO_LINK = "waiting_for_video_link"  # Data: {platform, format}
WAITING_FOR_FORMAT_SELECTION = "waiting_for_format_selection"  # Data: platform
AI_CHAT_ACTIVE = "ai_chat_active"
METRO_BROWSING = "metro_browsing"
TOOLS_MENU_ACTIVE = "tools_menu_active"
DEVELOPER_MENU_ACTIVE = "developer_menu_active"
METRO_SELECTION = "metro_selection"  # Data: selection dict
ADMIN_MENU_ACTIVE = "admin_menu_active"
AI_MENU_ACTIVE = "ai_menu_active"

# --- ASYNC HELPERS ---


async def set_state(user_id: int | str, state_name: str, data: dict | None = None) -> None:
    """Tek bir durum belirler. (Eskiden set.add() yapılıyordu)."""
    # Veritabanı çağrısı senkron olduğu için thread içinde çalıştırıyoruz
    await asyncio.to_thread(db.set_user_state, user_id, state_name, data)


async def check_state(user_id: int | str, state_name: str) -> bool:
    """Kullanıcının belirtilen durumda olup olmadığını kontrol eder."""
    current_state = await asyncio.to_thread(db.get_user_state, user_id)
    return bool(current_state and current_state.get("state_name") == state_name)


async def get_state(user_id: int | str) -> str | None:
    """Kullanıcının aktif durum adını döndürür. Yoksa None."""
    s = await asyncio.to_thread(db.get_user_state, user_id)
    return s.get("state_name") if s else None


async def get_data(user_id: int | str) -> dict:
    """Kullanıcının o anki durumuna ait veriyi (JSON) döndürür."""
    s = await asyncio.to_thread(db.get_user_state, user_id)
    return s.get("state_data", {}) if s else {}


async def update_data(user_id: int | str, partial_data: dict) -> None:
    """Aktif state verisini merge eder; state yoksa sessizce çıkar."""
    current_state = await asyncio.to_thread(db.get_user_state, user_id)
    if not current_state:
        return

    merged_data = {**current_state.get("state_data", {}), **partial_data}
    await asyncio.to_thread(db.set_user_state, user_id, current_state["state_name"], merged_data)


async def clear_user_states(user_id: int | str) -> None:
    """Kullanıcının tüm aktif durumlarını temizler (Veritabanından siler)."""
    await asyncio.to_thread(db.clear_user_state, user_id)


# For compatibility during refactor, some direct dict/set access might exist in old code.
# We must remove them.
