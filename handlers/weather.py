import html
import logging
from datetime import datetime as dt
from datetime import timedelta

import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes as CT

import database as db
import state
from config import OPENWEATHERMAP_API_KEY
from errors import get_error_message
from rate_limiter import rate_limit
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils import inline_keyboards as kb
from utils.middleware import production_handler

MAX_WEATHER_CACHE_SIZE = 100
_weather_cache = {}
WEATHER_CACHE_TTL = timedelta(minutes=10)
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)


def _evict_expired_cache():
    now = dt.now()
    keys = [k for k, v in _weather_cache.items() if now >= v["expires"]]
    for k in keys:
        del _weather_cache[k]
    if len(_weather_cache) > MAX_WEATHER_CACHE_SIZE:
        s_keys = sorted(_weather_cache.keys(), key=lambda k: _weather_cache[k]["expires"])
        for k in s_keys[: len(_weather_cache) - MAX_WEATHER_CACHE_SIZE]:
            del _weather_cache[k]


logger = logging.getLogger(__name__)


async def handle_missing_api_key(update: Update, lang: str) -> None:
    text = get_error_message("api_error", lang)
    markup = kb.get_tools_keyboard(lang)

    if update.callback_query:
        await update.callback_query.answer(text, show_alert=True)
        await update.callback_query.message.edit_text(text, reply_markup=markup)
        return

    await update.message.reply_text(text, reply_markup=markup)


@production_handler
@rate_limit("heavy")
async def weather_command(update: Update, context: CT):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    if not OPENWEATHERMAP_API_KEY:
        await handle_missing_api_key(update, lang)
        return

    text = TEXTS["weather_prompt_city"][lang]
    markup = kb.get_weather_cities_keyboard(lang)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text, reply_markup=markup)

    await state.set_state(user_id, state.WAITING_FOR_WEATHER_CITY, {})


async def get_weather_data(update: Update, context: CT, city_name):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    api_key = OPENWEATHERMAP_API_KEY

    # Cache Check
    city_lower = city_name.lower().strip()
    cache_key = f"{city_lower}_{lang}"
    now = dt.now()

    if cache_key in _weather_cache and now < _weather_cache[cache_key]["expires"]:
        data = _weather_cache[cache_key]["data"]
        await send_weather_message(update, context, data, lang)
        return

    # API Call
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric&lang={lang}"
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session, session.get(url) as resp:
            api_data = await resp.json()

        if api_data.get("cod") == 200:
            data = {
                "city": api_data["name"],
                "temp": api_data["main"]["temp"],
                "feels_like": api_data["main"]["feels_like"],
                "description": api_data["weather"][0]["description"].title(),
                "humidity": api_data["main"]["humidity"],
                "wind_speed": api_data["wind"]["speed"],
            }
            # Cache
            _evict_expired_cache()
            _weather_cache[cache_key] = {"data": data, "expires": now + WEATHER_CACHE_TTL}

            await send_weather_message(update, context, data, lang)
        else:
            await send_error(update, TEXTS["weather_city_not_found"][lang])

    except Exception as e:
        logger.error(f"Weather API Error: {e}")
        await send_error(update, TEXTS["weather_api_error"][lang])


async def send_weather_message(update: Update, context: CT, data, lang):
    display_city = data["city"]
    if lang == "ru":
        cities_en = [
            "Istanbul",
            "Ankara",
            "Kazan",
            "St. Petersburg",
            "Paris",
            "London",
            "Moscow",
            "New York",
            "Berlin",
            "Tokyo",
        ]
        cities_ru = [
            "Стамбул",
            "Анкара",
            "Казань",
            "Санкт-Петербург",
            "Париж",
            "Лондон",
            "Москва",
            "Нью-Йорк",
            "Берлин",
            "Токио",
        ]
        if display_city in cities_en:
            display_city = cities_ru[cities_en.index(display_city)]
        elif display_city == "Istanbul Province":
            display_city = "Стамбул"

    msg = TEXTS["weather_current"][lang].format(
        city=html.escape(display_city),
        temp=data["temp"],
        feels_like=data["feels_like"],
        description=html.escape(data["description"]),
        humidity=data["humidity"],
        wind_speed=data["wind_speed"],
    )

    weather_menu_text = {"tr": "🔙 Hava Durumu Menüsü", "en": "🔙 Weather Menu", "ru": "🔙 Меню погоды"}.get(
        lang, "🔙 Weather Menu"
    )
    keyboard = [
        [InlineKeyboardButton(TEXTS["weather_forecast_button"][lang], callback_data=f"FORECAST:{data['city']}")],
        [InlineKeyboardButton("🔄", callback_data=f"WEATHER:CITY:{data['city']}")],
        [InlineKeyboardButton(weather_menu_text, callback_data="WEATHER:MENU")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=markup, parse_mode="HTML")


async def send_error(update, text):
    if update.callback_query:
        await update.callback_query.answer(text, show_alert=True)
    else:
        await update.message.reply_text(text)


async def get_forecast_data(update: Update, context: CT, city, lang):
    api_key = OPENWEATHERMAP_API_KEY
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang={lang}"

    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session, session.get(url) as resp:
            data = await resp.json()

        if data.get("cod") != "200":
            await send_error(update, "Forecast Error")
            return

        # Simplistic forecast parsing (first 5 distinct days)
        lines = [f"📅 <b>Forecast: {city}</b>"]
        seen_days = set()
        count = 0

        for item in data["list"]:
            dt_txt = item["dt_txt"]
            day = dt_txt.split(" ")[0]
            if day not in seen_days:
                seen_days.add(day)
                temp = round(item["main"]["temp"])
                desc = item["weather"][0]["description"].title()
                icon = "🌤️"
                lines.append(f"• {day}: {temp}°C, {desc} {icon}")
                count += 1
                if count >= 5:
                    break

        text = "\n".join(lines)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"WEATHER:CITY:{city}")]])

        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Forecast Error: {e}")
        await send_error(update, TEXTS["weather_api_error"][lang])


async def weather_callback_handler(update: Update, context: CT):
    query = update.callback_query
    data = query.data

    if data == "WEATHER:MENU" or data == callbacks.TOOL_WEATHER:
        await weather_command(update, context)
    elif data.startswith("WEATHER:CITY:"):
        city = data.split(":")[-1]
        await get_weather_data(update, context, city)
    elif data.startswith("FORECAST:"):
        city = data.split(":")[-1]
        user_id = update.effective_user.id
        lang = await db.get_user_lang(user_id)
        await get_forecast_data(update, context, city, lang)


async def handle_weather_input(update: Update, context: CT):
    if update.message and update.message.text:
        await get_weather_data(update, context, update.message.text)


def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button, router

    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CallbackQueryHandler(weather_callback_handler, pattern=r"^(WEATHER:|FORECAST:|TOOL:WEATHER)"))
    router.register(state.WAITING_FOR_WEATHER_CITY, handle_weather_input)
    register_button("weather_main_button", weather_command)
    logger.info("✅ Weather module loaded (Inline)")
