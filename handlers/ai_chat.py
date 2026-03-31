import asyncio
import logging
import time
from datetime import datetime

import pytz
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import ContextTypes as CT

import database as db
import state
from config import ADMIN_IDS, AI_DAILY_LIMIT, OPENROUTER_API_KEY, TIMEZONE
from errors import get_error_message
from rate_limiter import rate_limit
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils import inline_keyboards as kb
from utils.middleware import production_handler

logger = logging.getLogger(__name__)

client = None
if OPENROUTER_API_KEY:
    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://github.com/kagandms/AskViraBot",
                "X-Title": "ViraBot",
            },
        )
    except Exception as e:
        logger.error(f"AI client initialization failed: {e}", exc_info=True)

AI_MODEL = "google/gemini-2.0-pro-exp-02-05:free"


def get_today_str(current_time: datetime | None = None) -> str:
    timezone = pytz.timezone(TIMEZONE)

    if current_time is None:
        localized_time = datetime.now(timezone)
    elif current_time.tzinfo is None:
        localized_time = timezone.localize(current_time)
    else:
        localized_time = current_time.astimezone(timezone)

    return localized_time.date().isoformat()


async def get_user_remaining_quota_async(user_id: int) -> int:
    today = get_today_str()
    used = await asyncio.to_thread(db.get_ai_daily_usage, user_id, today)
    limit = 999 if user_id in ADMIN_IDS else AI_DAILY_LIMIT
    return max(0, limit - used)


async def increment_usage_async(user_id: int) -> None:
    today = get_today_str()
    await asyncio.to_thread(db.increment_ai_usage, user_id, today)


# --- HANDLERS ---
@production_handler
@rate_limit("heavy")
async def ai_menu(update: Update, context: CT) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    remaining = await get_user_remaining_quota_async(user_id)
    msg_text = (
        TEXTS["ai_menu_prompt_admin"][lang]
        if user_id in ADMIN_IDS
        else TEXTS["ai_menu_prompt"][lang].format(remaining=remaining, limit=AI_DAILY_LIMIT)
    )

    markup = kb.get_ai_menu_keyboard(lang)

    if update.callback_query:
        await update.callback_query.message.edit_text(msg_text, reply_markup=markup, parse_mode="HTML")
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        sent = await update.message.reply_text(msg_text, reply_markup=markup, parse_mode="HTML")
        await state.set_state(user_id, state.AI_MENU_ACTIVE, {"message_id": sent.message_id})


async def start_ai_chat(update: Update, context: CT) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    rem = await get_user_remaining_quota_async(user_id)
    if rem <= 0:
        await update.callback_query.message.edit_text(
            TEXTS["ai_limit_reached"][lang], reply_markup=kb.get_main_keyboard(lang), parse_mode="HTML"
        )
        return

    await state.clear_user_states(user_id)
    await state.set_state(user_id, state.AI_CHAT_ACTIVE, {"messages": []})

    text = TEXTS["ai_chat_started"][lang]
    markup = kb.get_ai_chat_keyboard(lang)

    await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


async def end_ai_chat(update: Update, context: CT) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await state.clear_user_states(user_id)
    await update.callback_query.answer(TEXTS["ai_chat_ended"][lang])

    # Return to AI Menu
    await ai_menu(update, context)


async def handle_ai_message(update: Update, context: CT) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    user_msg = update.message.text

    rem = await get_user_remaining_quota_async(user_id)
    if rem <= 0:
        await update.message.reply_text(TEXTS["ai_limit_reached"][lang])
        return

    if not client:
        await update.message.reply_text(get_error_message("api_error", lang))
        return

    # Typing...
    try:
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
    except Exception:
        logger.debug("Failed to send chat action for AI request", exc_info=True)

    # Thinking...
    ai_msg = await update.message.reply_text("🤔...")

    try:
        state_data = await state.get_data(user_id)
        history = state_data.get("messages", []) if state_data else []

        sys_prompt = "You are ViraBot assistant. Be concise. Use emojis. Reply in user's language."
        messages = [{"role": "system", "content": sys_prompt}, *history, {"role": "user", "content": user_msg}]

        stream = await client.chat.completions.create(model=AI_MODEL, messages=messages, max_tokens=1000, stream=True)

        full_response = ""
        buffer = ""
        last_update = time.time()

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                buffer += delta
                full_response += delta

                if time.time() - last_update > 1.5:
                    try:
                        await ai_msg.edit_text(buffer + " ▌")
                        last_update = time.time()
                    except Exception:
                        logger.debug("Failed to stream AI partial response", exc_info=True)

        # Finalize
        final_text = full_response.strip()
        if not final_text:
            await ai_msg.edit_text(get_error_message("api_error", lang), reply_markup=kb.get_ai_chat_keyboard(lang))
            return

        if user_id not in ADMIN_IDS:
            await increment_usage_async(user_id)

        markup = kb.get_ai_chat_keyboard(lang)  # Attached End Chat button

        await ai_msg.edit_text(final_text, reply_markup=markup)

        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": final_text})
        if len(history) > 10:
            history = history[-10:]

        await state.set_state(user_id, state.AI_CHAT_ACTIVE, {"messages": history})

    except Exception as e:
        logger.error(f"AI Error: {e}", exc_info=True)
        await ai_msg.edit_text(get_error_message("generic_error", lang), reply_markup=kb.get_ai_chat_keyboard(lang))


async def handle_ai_callback(update: Update, context: CT):
    query = update.callback_query
    data = query.data

    if data == callbacks.AI_START:
        await start_ai_chat(update, context)
    elif data == callbacks.AI_END:
        await end_ai_chat(update, context)
    elif data == callbacks.MENU_AI:
        await ai_menu(update, context)


def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button, router

    app.add_handler(CommandHandler("ai", ai_menu))
    app.add_handler(CallbackQueryHandler(handle_ai_callback, pattern=r"^(AI:|MENU:AI)"))

    router.register(state.AI_CHAT_ACTIVE, handle_ai_message)

    register_button("ai_main_button", ai_menu)
    logger.info("✅ AI module loaded (Inline)")
