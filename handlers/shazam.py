import html
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

# from shazamio import Shazam # Will import inside function to avoid import error if not installed yet
import database as db
from errors import get_error_message
from texts import TEXTS
from utils import callbacks

logger = logging.getLogger(__name__)
from utils.middleware import production_handler


async def recognize_file(file_path: str):
    """Recognize music from file using Shazam"""
    from shazamio import Shazam

    shazam = Shazam()
    out = await shazam.recognize(file_path)
    return out


def format_shazam_result(result, lang):
    """Format Shazam result for display"""
    track = result.get("track")
    if not track:
        return None

    title = track.get("title", "Unknown")
    subtitle = track.get("subtitle", "Unknown")
    images = track.get("images", {})
    cover_art = images.get("coverarthq") or images.get("coverart")

    sections = track.get("sections", [])
    for section in sections:
        if section.get("type") == "LYRICS":
            section.get("text")
            break

    # Basic formatting
    msg = f"🎵 <b>{html.escape(title)}</b>\n👤 {html.escape(subtitle)}\n"

    # Metadata shortcuts
    providers = track.get("hub", {}).get("providers", [])
    links = []
    for provider in providers:
        capt = provider.get("caption")
        actions = provider.get("actions", [])
        for action in actions:
            uri = action.get("uri")
            if uri and capt:
                links.append(f'<a href="{uri}">{html.escape(capt)}</a>')

    if links:
        msg += "\n" + " | ".join(links)

    return {"text": msg, "photo": cover_art}


import state


@production_handler
async def handle_shazam_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Shazam input (audio, voice, video, link)"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    msg_obj = update.message
    text = msg_obj.text

    # Delete user input
    try:
        await update.message.delete()
    except Exception as e:
        logger.debug(f"Shazam input delete error: {e}")

    process_msg_text = TEXTS["shazam_processing"][lang]
    processing_msg = await update.message.reply_text(process_msg_text)

    file_path = None

    try:
        # 1. Check for Files
        file_id = None
        if msg_obj.audio:
            file_id = msg_obj.audio.file_id
        elif msg_obj.voice:
            file_id = msg_obj.voice.file_id
        elif msg_obj.video:
            file_id = msg_obj.video.file_id
        elif msg_obj.video_note:
            file_id = msg_obj.video_note.file_id
        elif msg_obj.document:
            mime = msg_obj.document.mime_type
            if mime and ("audio" in mime or "video" in mime):
                file_id = msg_obj.document.file_id

        if file_id:
            # Download file
            new_file = await context.bot.get_file(file_id)
            file_name = f"temp_shazam_{user_id}_{file_id[:10]}"
            file_path = f"/tmp/{file_name}"
            await new_file.download_to_drive(file_path)

        # 2. Check for Links
        elif text and ("http" in text):
            # Validate URL domain before downloading if needed, but yt-dlp supports almost everything.
            import yt_dlp

            file_path = f"/tmp/temp_shazam_link_{user_id}.mp3"

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": file_path,
                "noplaylist": True,
                "quiet": True,
            }
            if os.path.exists(file_path):
                os.remove(file_path)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Run download in a separate thread so it doesn't block the async event loop
                import asyncio

                await asyncio.to_thread(ydl.download, [text])

        else:
            # Invalid input
            await processing_msg.delete()
            return  # Ignore non-matching text

        # 3. Recognize
        if file_path and os.path.exists(file_path):
            result = await recognize_file(file_path)
            formatted = format_shazam_result(result, lang)

            await processing_msg.delete()

            if formatted:
                if formatted["photo"]:
                    await update.message.reply_photo(
                        photo=formatted["photo"], caption=formatted["text"], parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text(formatted["text"], parse_mode="HTML")
            else:
                await update.message.reply_text(TEXTS["shazam_not_found"][lang])

            # Cleanup
            os.remove(file_path)
        else:
            await processing_msg.delete()
            download_failed_texts = {
                "tr": "❌ İndirme başarısız oldu.",
                "en": "❌ Download failed.",
                "ru": "❌ Ошибка загрузки.",
            }
            await update.message.reply_text(download_failed_texts.get(lang, download_failed_texts["en"]))

    except Exception as e:
        try:
            await processing_msg.delete()
        except Exception as del_err:
            logger.debug(f"Shazam processing msg delete error: {del_err}")
        logger.error(f"Shazam error for user {user_id}: {e}")
        await update.message.reply_text(get_error_message("generic_error", lang))
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


@production_handler
async def start_shazam_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Shazam mode"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Cleanup context
    await state.clear_user_states(user_id)
    await state.set_state(user_id, state.WAITING_FOR_SHAZAM, {})

    from utils import callbacks
    from utils import inline_keyboards as kb

    markup = kb.get_back_keyboard(lang, callbacks.TOOL_BACK)
    text = TEXTS["shazam_menu_prompt"][lang]

    if update.callback_query:
        # Edit existing message
        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        # Send new message
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


async def handle_shazam_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == callbacks.TOOL_SHAZAM:
        await start_shazam_mode(update, context)


def setup(app):
    import logging

    from telegram.ext import CallbackQueryHandler, CommandHandler

    import state
    from core.router import register_button, router

    # 1. Commands
    app.add_handler(CommandHandler("shazam", start_shazam_mode))
    app.add_handler(CallbackQueryHandler(handle_shazam_callback, pattern=r"^TOOL:SHAZAM"))

    # 2. Router
    router.register(state.WAITING_FOR_SHAZAM, handle_shazam_input)

    # 3. Buttons
    register_button("shazam_main_button", start_shazam_mode)

    logging.getLogger(__name__).info("✅ Shazam module loaded (Inline)")
