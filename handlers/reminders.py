import asyncio
import logging
import re
from datetime import datetime, timedelta

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
import state
from config import TIMEZONE
from errors import get_error_message
from texts import TEXTS
from utils import callbacks, cleanup_context, format_remaining_time
from utils import inline_keyboards as kb

logger = logging.getLogger(__name__)


# --- INLINE HELPERS ---
async def show_reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    text = TEXTS["reminder_menu_prompt"][lang]
    markup = kb.get_reminder_keyboard(lang)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text, reply_markup=markup)


async def prompt_add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    await state.clear_user_states(user_id)

    text = TEXTS["remind_prompt_input"][lang]
    # Inline Back button
    markup = kb.get_back_keyboard(lang, callbacks.REMINDER_BACK)

    if update.callback_query:
        await update.callback_query.answer()
        msg = await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        message_id = getattr(msg, "message_id", update.callback_query.message.message_id)
    else:
        msg = await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
        message_id = msg.message_id

    await state.set_state(user_id, state.WAITING_FOR_REMINDER_INPUT, {"message_id": message_id})


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    reminders = await asyncio.to_thread(db.get_all_reminders_db)
    user_reminders = [r for r in reminders if str(r.user_id) == str(user_id)]

    if not user_reminders:
        text = TEXTS["no_reminders"][lang]
    else:
        now = datetime.now(pytz.utc)
        lines = []
        for i, r in enumerate(user_reminders, 1):
            try:
                dt = datetime.fromisoformat(r.time)
                rem = (dt - now).total_seconds()
                local_dt = dt.astimezone(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M")

                status = "✅" if rem > 0 else "⏰"
                lines.append(f"{i}. {status} <b>{local_dt}</b>: {r.message}")
            except:
                lines.append(f"{i}. ❓ {r.message}")

        text = TEXTS["reminders_header"][lang] + "\n\n" + "\n".join(lines)

    markup = kb.get_back_keyboard(lang, callbacks.REMINDER_BACK)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


async def delete_reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    reminders = await asyncio.to_thread(db.get_all_reminders_db)
    user_reminders = [r for r in reminders if str(r.user_id) == str(user_id)]

    if not user_reminders:
        await update.callback_query.answer(TEXTS["no_reminders"][lang])
        return

    keyboard = []
    for r in user_reminders:
        preview = r.message[:20] + "..." if len(r.message) > 20 else r.message
        # REM:DEL_EXEC:ID
        keyboard.append(
            [InlineKeyboardButton(f"🗑️ {preview}", callback_data=f"{callbacks.REMINDER_DELETE_EXEC}:{r.id}")]
        )

    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.REMINDER_BACK)])
    markup = InlineKeyboardMarkup(keyboard)

    text = TEXTS["prompt_select_reminder_to_delete"][lang]
    await update.callback_query.message.edit_text(text, reply_markup=markup)


async def delete_reminder_exec(update: Update, context: ContextTypes.DEFAULT_TYPE, rem_id):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await asyncio.to_thread(db.remove_reminder_db, int(rem_id))
    await update.callback_query.answer(TEXTS["reminder_deleted"][lang])
    await delete_reminder_menu(update, context)


async def process_reminder_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    text = update.message.text

    # Parse Logic (Same as before)
    match = re.match(r"^(\d{1,2}:\d{2})\s*(?:(\d{4}-\d{2}-\d{2})\s*)?(.*)$", text.strip())

    # Cleanup previous prompt
    await cleanup_context(context, user_id)
    try:
        await update.message.delete()
    except:
        pass

    if not match or not match.group(3).strip():
        await update.message.reply_text(TEXTS["remind_usage"][lang], parse_mode="HTML")
        return

    time_arg, date_arg, message = match.group(1), match.group(2), match.group(3).strip()
    istanbul_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(istanbul_tz)

    try:
        time_dt = datetime.strptime(time_arg, "%H:%M")
        if date_arg:
            target = istanbul_tz.localize(datetime.strptime(date_arg, "%Y-%m-%d")).replace(
                hour=time_dt.hour, minute=time_dt.minute
            )
        else:
            target = istanbul_tz.localize(datetime.combine(now.date(), time_dt.time()))
            if target < now:
                target += timedelta(days=1)

        rem_data = {
            "user_id": user_id,
            "chat_id": update.effective_chat.id,
            "time": target.astimezone(pytz.utc).isoformat(),
            "message": message,
        }

        rid = await asyncio.to_thread(db.add_reminder_db, rem_data)
        if rid is None:
            await state.clear_user_states(user_id)
            await update.message.reply_text(
                get_error_message("database_error", lang), reply_markup=kb.get_reminder_keyboard(lang)
            )
            return

        # Schedule Task
        rem_secs = (target - now).total_seconds()
        asyncio.create_task(reminder_task(context.application, update.effective_chat.id, message, rem_secs, rid))

        time_str = target.strftime("%Y-%m-%d %H:%M")
        success_text = TEXTS["reminder_set"][lang].format(
            time_str=time_str, message=message, remaining_time=format_remaining_time(rem_secs, lang)
        )

        await update.message.reply_text(success_text, reply_markup=kb.get_reminder_keyboard(lang))
        await state.clear_user_states(user_id)

    except Exception as e:
        logger.error(f"Reminder creation failed: {e}", exc_info=True)
        await state.clear_user_states(user_id)
        await update.message.reply_text(
            get_error_message("generic_error", lang), reply_markup=kb.get_reminder_keyboard(lang)
        )


async def reminder_task(application, chat_id, message, wait_seconds, reminder_id):
    await asyncio.sleep(wait_seconds)
    try:
        await application.bot.send_message(chat_id=chat_id, text=f"🔔 Reminder: {message}")
        if reminder_id:
            await asyncio.to_thread(db.remove_reminder_db, reminder_id)
    except Exception as e:
        logger.error(f"Reminder failed: {e}")


async def start_pending_reminders(application):
    # (Preserved logic)
    reminders = await asyncio.to_thread(db.get_all_reminders_db)
    now = datetime.now(pytz.utc)
    for r in reminders:
        try:
            if not r.chat_id or not r.message or not r.time:
                logger.warning(f"Skipping incomplete reminder row id={r.id}")
                continue

            dt = datetime.fromisoformat(r.time)
            if dt > now:
                secs = (dt - now).total_seconds()
                asyncio.create_task(reminder_task(application, r.chat_id, r.message, secs, r.id))
            else:
                await asyncio.to_thread(db.remove_reminder_db, r.id)
        except:
            pass


# --- ROUTER ---
async def handle_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == callbacks.REMINDER_BACK:
        await show_reminder_menu(update, context)
    elif data == callbacks.REMINDER_ADD:
        await prompt_add_reminder(update, context)
    elif data == callbacks.REMINDER_LIST:
        await list_reminders(update, context)
    elif data == callbacks.REMINDER_DELETE_MENU:
        await delete_reminder_menu(update, context)
    elif data.startswith(callbacks.REMINDER_DELETE_EXEC):
        rid = data.split(":")[-1]
        await delete_reminder_exec(update, context, rid)
    elif data == callbacks.TOOL_REMINDER:
        await show_reminder_menu(update, context)


# --- SETUP ---
def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button, router

    app.add_handler(CommandHandler("remind", show_reminder_menu))

    app.add_handler(CommandHandler("reminders", show_reminder_menu))
    app.add_handler(CallbackQueryHandler(handle_reminder_callback, pattern=r"^(REM:|TOOL:REMINDER)"))

    # Router
    router.register(state.WAITING_FOR_REMINDER_INPUT, process_reminder_input)

    register_button("reminder_main_button", show_reminder_menu)
    register_button("reminder_add", prompt_add_reminder)
    register_button("reminder_list", list_reminders)
    register_button("reminder_delete", delete_reminder_menu)
    logger.info("✅ Reminders module loaded (Inline)")
