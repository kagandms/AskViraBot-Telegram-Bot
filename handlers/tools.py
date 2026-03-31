import asyncio
import html
import logging
import os
import uuid
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)
import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
import state
from config import TIMEZONE
from errors import get_error_message
from rate_limiter import rate_limit
from texts import SOCIAL_MEDIA_LINKS, TEXTS
from utils import callbacks, cleanup_context, is_back_button
from utils import inline_keyboards as kb
from utils.middleware import production_handler


# --- ZAMAN KOMUTU ---
@production_handler
async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%H:%M:%S")

    # Callback ile geldiyse
    if update.callback_query:
        await update.callback_query.answer(f"🕒 Saat: {now}")
        return

    await update.message.reply_text(f"🕒 Saat: {now}")


# --- TOOLS MENU ---
@production_handler
async def tools_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Araçlar menüsünü gösterir."""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Cleanup
    await cleanup_context(context, user_id)

    text = TEXTS["tools_menu_prompt"][lang]
    markup = kb.get_tools_keyboard(lang)

    if update.callback_query:
        msg = update.callback_query.message
        if msg.photo or msg.video or msg.document or msg.audio or msg.voice:
            try:
                await msg.delete()
            except:
                pass
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)
        else:
            await update.callback_query.message.edit_text(text=text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)

    await state.clear_user_states(user_id)


# --- QR KOD ---
@rate_limit("heavy")
async def qrcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    if context.args:
        data = " ".join(context.args)
        await generate_and_send_qr(update, context, data)
    else:
        await state.clear_user_states(user_id)

        # Cleanup
        if update.callback_query:
            # Inline interaction: Edit message to ask for input
            await update.callback_query.answer()
            msg = await update.callback_query.message.edit_text(
                TEXTS["qrcode_prompt_input"][lang], reply_markup=kb.get_back_keyboard(lang, callbacks.TOOL_BACK)
            )
            message_id = getattr(msg, "message_id", update.callback_query.message.message_id)
        else:
            try:
                await update.message.delete()
            except:
                pass

            msg = await update.message.reply_text(
                TEXTS["qrcode_prompt_input"][lang], reply_markup=kb.get_back_keyboard(lang, callbacks.TOOL_BACK)
            )
            message_id = msg.message_id

        await state.set_state(user_id, state.WAITING_FOR_QR_DATA, {"message_id": message_id})


async def handle_qr_input_from_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wrapper for state router - gets text from message and calls generate_and_send_qr"""
    if update.message and update.message.text:
        # Check if text is "Back" (Legacy support)
        if is_back_button(update.message.text):
            await tools_menu_command(update, context)
            return

        await generate_and_send_qr(update, context, update.message.text)


async def generate_and_send_qr(update: Update, context: ContextTypes.DEFAULT_TYPE, data):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    file_path = f"qr_{user_id}_{uuid.uuid4().hex[:8]}.png"

    try:
        img = qrcode.make(data)
        img.save(file_path)

        await asyncio.to_thread(db.log_qr_usage, user_id, data)

        with open(file_path, "rb") as photo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=TEXTS["qrcode_generated"][lang].format(data=html.escape(data)),
                reply_markup=kb.get_back_keyboard(lang, callbacks.TOOL_BACK),
            )

        # Cleanup QR input prompt
        await cleanup_context(context, user_id)

    except Exception as e:
        logger.error(f"QR generation error for user {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text=get_error_message("generic_error", lang))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    await state.clear_user_states(user_id)


# --- GELİŞTİRİCİ ---
def get_developer_keyboard_inline(lang):
    """Inline Developer Keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🌐 Web", url=SOCIAL_MEDIA_LINKS["website"]),
            InlineKeyboardButton("📸 Instagram", url=SOCIAL_MEDIA_LINKS["instagram"]),
        ],
        [
            InlineKeyboardButton("✈️ Telegram", url=SOCIAL_MEDIA_LINKS["telegram"]),
            InlineKeyboardButton("💼 LinkedIn", url=SOCIAL_MEDIA_LINKS["linkedin"]),
        ],
        [InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.MENU_MAIN)],
    ]
    return InlineKeyboardMarkup(keyboard)


@production_handler
async def show_developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    dev_text = {
        "tr": "👨‍💻 <b>Geliştirici Bilgileri</b>\n\nSosyal medya hesaplarıma aşağıdaki bağlantılardan ulaşabilirsiniz:",
        "en": "👨‍💻 <b>Developer Info</b>\n\nYou can reach my social media accounts through the links below:",
        "ru": "👨‍💻 <b>Информация о разработчике</b>\n\nВы можете связаться со мной через соцсети по ссылкам ниже:",
    }

    text = dev_text.get(lang, dev_text["en"])
    markup = get_developer_keyboard_inline(lang)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


async def handle_tools_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if data == callbacks.MENU_TOOLS:
        await tools_menu_command(update, context)
    elif data == callbacks.MENU_DEVELOPER:
        await show_developer_info(update, context)
    elif data == "back_to_main_menu":
        # Legacy or social media back, route to main menu
        from handlers.general import menu_command

        await menu_command(update, context)
    elif data == callbacks.TOOL_QR:
        await qrcode_command(update, context)
    elif data == callbacks.TOOL_BACK:
        await tools_menu_command(update, context)


# --- MODULAR SETUP ---
def setup(app):
    import state
    from core.router import register_button, router

    # 1. Commands
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("qrcode", qrcode_command))
    app.add_handler(CommandHandler("developer", show_developer_info))
    app.add_handler(CommandHandler("tools", tools_menu_command))

    # 2. Callbacks
    app.add_handler(
        CallbackQueryHandler(
            handle_tools_callback, pattern=r"^(MENU:TOOLS|MENU:DEV|TOOL:QR|TOOL:BACK|back_to_main_menu)$"
        )
    )

    # 3. Router
    router.register(state.WAITING_FOR_QR_DATA, handle_qr_input_from_state)

    # 4. Buttons
    register_button("developer_main_button", show_developer_info)
    register_button("time", time_command)
    register_button("qrcode_button", qrcode_command)
    register_button("tools_main_button", tools_menu_command)
    register_button("back_to_tools", tools_menu_command)

    logger.info("✅ Tools module loaded")
