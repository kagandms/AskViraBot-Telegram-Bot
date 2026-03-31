"""
Metro Istanbul Handler (Inline Version)
Provides real-time metro departure times using IBB Metro Istanbul API.
"""

import asyncio
import logging
from datetime import datetime

import aiohttp
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
import state
from rate_limiter import rate_limit
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils.middleware import production_handler

logger = logging.getLogger(__name__)

# Istanbul timezone
ISTANBUL_TZ = pytz.timezone("Europe/Istanbul")
METRO_API_BASE = "https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2"

# --- CACHING SYSTEM ---
_http_session = None


async def get_http_session():
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
    return _http_session


async def close_http_session():
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()


from .metro_data import METRO_DIRECTIONS, METRO_LINES, METRO_STATIONS


async def fetch_lines():
    return METRO_LINES


async def fetch_stations_by_line(line_id):
    return METRO_STATIONS.get(str(line_id), [])


async def fetch_directions_by_line(line_id):
    return METRO_DIRECTIONS.get(str(line_id), [])


async def fetch_timetable(station_id, direction_id):
    try:
        now = datetime.now(ISTANBUL_TZ).strftime("%Y-%m-%dT%H:%M:%S+03:00")
        payload = {"BoardingStationId": station_id, "DirectionId": direction_id, "DateTime": now}
        session = await get_http_session()
        async with session.post(
            f"{METRO_API_BASE}/GetTimeTable", json=payload, headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            if data.get("Success"):
                return data.get("Data", [])
    except Exception as e:
        logger.error(f"Metro API Error: {e}")
    return []


# --- INLINE HANDLERS ---


@rate_limit("heavy")
@production_handler
async def metro_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    # Fetch Lines
    lines = await fetch_lines()
    if not lines:
        await update.message.reply_text(TEXTS["metro_api_error"][lang])
        return

    # Filter M lines
    metro_lines = [line for line in lines if line.get("Name", "").startswith("M")]

    # Build Keyboard
    keyboard = []
    row = []
    for line in metro_lines:
        name = line.get("Name", "")
        lid = line.get("Id")
        if name and lid:
            row.append(InlineKeyboardButton(f"🚇 {name}", callback_data=f"{callbacks.METRO_LINE_PREFIX}{lid}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)

    # Add Favorites & Back
    favorites_label = {"tr": "⭐ Favoriler", "en": "⭐ Favorites", "ru": "⭐ Избранное"}
    keyboard.append([InlineKeyboardButton(favorites_label.get(lang, "⭐"), callback_data=callbacks.METRO_FAV_LIST)])
    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.TOOL_BACK)])

    text = TEXTS["metro_menu_prompt"][lang]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text, reply_markup=markup)


async def show_stations(update: Update, context: ContextTypes.DEFAULT_TYPE, line_id: str):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    stations = await fetch_stations_by_line(line_id)

    keyboard = []
    row = []
    for station in stations:
        name = station.get("Description", station.get("Name", ""))
        sid = station.get("Id")
        if name and sid:
            row.append(
                InlineKeyboardButton(f"📍 {name}", callback_data=f"{callbacks.METRO_STATION_PREFIX}{line_id}:{sid}")
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.METRO_MENU)])
    markup = InlineKeyboardMarkup(keyboard)

    # Find line name
    line_name = ""
    lines = await fetch_lines()
    for line_item in lines:
        if str(line_item.get("Id")) == str(line_id):
            line_name = line_item.get("Name", "")
            break

    text = f"📍 🚇 <b>{line_name}</b>\n\n{TEXTS['metro_select_station'][lang].format(line='')}"
    await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


async def show_directions(update: Update, context: ContextTypes.DEFAULT_TYPE, line_id: str, station_id: str):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    directions = await fetch_directions_by_line(line_id)
    keyboard = []
    for direction in directions:
        name = direction.get("DirectionName", "")
        did = direction.get("DirectionId")
        if name and did:
            # Callback: METRO:DIR:LINE_ID:STATION_ID:DIR_ID
            cb = f"{callbacks.METRO_DIR_PREFIX}{line_id}:{station_id}:{did}"
            keyboard.append([InlineKeyboardButton(f"➡️ {name}", callback_data=cb)])

    # Back to Stations
    keyboard.append(
        [
            InlineKeyboardButton(
                TEXTS["back_button_inline"][lang], callback_data=f"{callbacks.METRO_LINE_PREFIX}{line_id}"
            )
        ]
    )
    markup = InlineKeyboardMarkup(keyboard)

    text = TEXTS["metro_select_direction"][lang]
    await update.callback_query.message.edit_text(text, reply_markup=markup)


async def show_timetable_inline(update: Update, context: ContextTypes.DEFAULT_TYPE, line_id, station_id, direction_id):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    loading_texts = {"tr": "⏳ Yükleniyor...", "en": "⏳ Loading...", "ru": "⏳ Загрузка..."}
    await update.callback_query.answer(loading_texts.get(lang, "Loading..."))

    timetable_data = await fetch_timetable(station_id, direction_id)

    if not timetable_data:
        text = TEXTS["metro_no_departures"][lang]
    else:
        timetable = timetable_data[0]
        times = timetable.get("TimeInfos", {}).get("Times", [])
        if not times:
            text = TEXTS["metro_no_departures"][lang]
        else:
            now = datetime.now(ISTANBUL_TZ)
            lines = []
            for time_str in times[:6]:
                try:
                    h, m = map(int, time_str.split(":"))
                    dep = now.replace(hour=h, minute=m, second=0)
                    if dep < now:
                        continue
                    mins = int((dep - now).total_seconds() / 60)
                    lines.append(f"🚇 {time_str} ({mins} min)")
                except:
                    lines.append(f"🚇 {time_str}")

            header = TEXTS["metro_departures_header"][lang].format(line="", station="", direction="")
            text = f"{header}\n\n" + "\n".join(lines) if lines else TEXTS["metro_no_departures"][lang]

    # Keyboard: Refresh, Back, Favorite
    refresh_text = {"tr": "🔄 Yenile", "en": "🔄 Refresh", "ru": "🔄 Обновить"}
    fav_text = {"tr": "⭐ Favoriye Ekle", "en": "⭐ Add to Favorites", "ru": "⭐ В избранное"}

    keyboard = [
        [
            InlineKeyboardButton(
                refresh_text.get(lang, "Refresh"),
                callback_data=f"{callbacks.METRO_DIR_PREFIX}{line_id}:{station_id}:{direction_id}",
            )
        ],
        [
            InlineKeyboardButton(
                fav_text.get(lang, "Fav"),
                callback_data=f"{callbacks.METRO_FAV_ADD}:{line_id}:{station_id}:{direction_id}",
            )
        ],
        [
            InlineKeyboardButton(
                TEXTS["back_button_inline"][lang],
                callback_data=f"{callbacks.METRO_STATION_PREFIX}{line_id}:{station_id}",
            )
        ],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        # Message not modified
        pass


# --- FAVORITES ---
async def add_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE, data_str: str):
    parts = data_str.split(":")
    if len(parts) < 6:
        return
    line_id, station_id, direction_id = parts[3], parts[4], parts[5]

    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Need names for DB - lookup
    l_name, s_name, d_name = "Line", "Station", "Dir"

    lines = await fetch_lines()
    for line_item in lines:
        if str(line_item["Id"]) == str(line_id):
            l_name = line_item["Name"]
            break

    stats = await fetch_stations_by_line(line_id)
    for s in stats:
        if str(s["Id"]) == str(station_id):
            s_name = s.get("Description", "")
            break

    dirs = await fetch_directions_by_line(line_id)
    for d in dirs:
        if str(d["DirectionId"]) == str(direction_id):
            d_name = d["DirectionName"]
            break

    try:
        await asyncio.to_thread(
            db.add_metro_favorite,
            user_id=user_id,
            line_id=str(line_id),
            line_name=l_name,
            station_id=str(station_id),
            station_name=s_name,
            direction_id=str(direction_id),
            direction_name=d_name,
        )

        success_texts = {"tr": "⭐ Favorilere Eklendi", "en": "⭐ Added to Favorites", "ru": "⭐ В избранном"}
        await update.callback_query.answer(success_texts.get(lang, "Added"))
    except Exception as e:
        logger.error(f"Failed to add metro favorite: {e}")
        await update.callback_query.answer("Error", show_alert=True)
        return

    # Update button visually to show it's added
    kb = update.callback_query.message.reply_markup.inline_keyboard
    new_kb = []
    for row in kb:
        new_row = []
        for btn in row:
            if btn.callback_data == data_str:
                fav_text_added = {"tr": "✅ Favorilere Eklendi", "en": "✅ Added to Favs", "ru": "✅ В избранном"}
                new_row.append(InlineKeyboardButton(fav_text_added.get(lang, "✅ Fav"), callback_data="dummy"))
            else:
                new_row.append(btn)
        new_kb.append(new_row)

    try:
        await update.callback_query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_kb))
    except:
        pass


async def list_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    favs = await asyncio.to_thread(db.get_metro_favorites, user_id)

    if not favs:
        await update.callback_query.answer("No favorites found.")
        return

    keyboard = []
    for fav in favs:
        # Callback: METRO:DIR:LINE:STAT:DIR (reuse functionality)
        cb = f"{callbacks.METRO_DIR_PREFIX}{fav['line_id']}:{fav['station_id']}:{fav['direction_id']}"
        text = f"⭐ {fav['station_name']} -> {fav.get('direction_name', '?')}"
        keyboard.append([InlineKeyboardButton(text, callback_data=cb)])

    # Delete Option
    del_text = {"tr": "🗑️ Düzenle/Sil", "en": "🗑️ Edit/Delete", "ru": "🗑️ Ред./Удалить"}
    keyboard.append([InlineKeyboardButton(del_text.get(lang, "Delete"), callback_data="METRO:FAV:DEL_MENU")])

    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.METRO_MENU)])
    markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text("⭐ Favorites:", reply_markup=markup)


async def delete_favorite_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    favs = await asyncio.to_thread(db.get_metro_favorites, user_id)

    keyboard = []
    for i, fav in enumerate(favs):
        cb = f"{callbacks.METRO_FAV_DEL}:{i}"
        text = f"🗑️ {fav['station_name']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=cb)])

    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.METRO_FAV_LIST)])
    markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text("🗑️ Select to delete:", reply_markup=markup)


async def delete_favorite_exec(update: Update, context: ContextTypes.DEFAULT_TYPE, idx):
    user_id = update.effective_user.id

    # Retrieve the list of favorites to get the station and direction ID from the index
    idx = int(idx)
    favs = await asyncio.to_thread(db.get_metro_favorites, user_id)
    if 0 <= idx < len(favs):
        fav = favs[idx]
        station_id_str = str(fav["station_id"])
        direction_id_str = str(fav["direction_id"])
        await asyncio.to_thread(db.remove_metro_favorite, user_id, station_id_str, direction_id_str)
        await update.callback_query.answer("Deleted.")
    else:
        await update.callback_query.answer("Error during deletion.")

    await list_favorites(update, context)


async def handle_metro_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if data == callbacks.METRO_MENU:
        await metro_menu_command(update, context)
    elif data == callbacks.METRO_FAV_LIST:
        await list_favorites(update, context)
    elif data == "METRO:FAV:DEL_MENU":
        await delete_favorite_menu(update, context)
    elif data.startswith(callbacks.METRO_LINE_PREFIX):
        # METRO:LINE:123
        line_id = data.split(":")[-1]
        await show_stations(update, context, line_id)
    elif data.startswith(callbacks.METRO_STATION_PREFIX):
        # METRO:STAT:LINE:STAT
        parts = data.split(":")
        await show_directions(update, context, parts[2], parts[3])
    elif data.startswith(callbacks.METRO_DIR_PREFIX):
        # METRO:DIR:LINE:STAT:DIR
        parts = data.split(":")
        await show_timetable_inline(update, context, parts[2], parts[3], parts[4])
    elif data.startswith(callbacks.METRO_FAV_ADD):
        await add_favorite(update, context, data)
    elif data.startswith(callbacks.METRO_FAV_DEL):
        idx = data.split(":")[-1]
        await delete_favorite_exec(update, context, idx)
    elif data == callbacks.TOOL_METRO or data == callbacks.METRO_LINES:
        await metro_menu_command(update, context)


# --- SETUP ---
def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button

    app.add_handler(CommandHandler("metro", metro_menu_command))
    app.add_handler(CallbackQueryHandler(handle_metro_callback, pattern=r"^(METRO:|TOOL:METRO)"))
    register_button("metro_main_button", metro_menu_command)
    logger.info("✅ Metro module loaded (Inline)")
