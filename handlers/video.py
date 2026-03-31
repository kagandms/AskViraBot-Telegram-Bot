import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes as CT

import database as db
import state
from rate_limiter import rate_limit
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils import inline_keyboards as kb
from utils.middleware import production_handler

logger = logging.getLogger(__name__)


# --- VALIDATION ---
def is_valid_video_url(url: str, platform: str) -> bool:
    valid_domains = {
        "tiktok": ["tiktok.com", "vm.tiktok.com"],
        "twitter": ["twitter.com", "x.com", "t.co"],
        "instagram": ["instagram.com", "instagr.am"],
    }
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return any(domain == d or domain.endswith("." + d) for d in valid_domains.get(platform, []))
    except:
        return False


def create_download_workspace(user_id: int | str) -> Path:
    return Path(tempfile.mkdtemp(prefix=f"vira_media_{user_id}_"))


def get_output_template(workspace: Path) -> str:
    return str(workspace / "media.%(ext)s")


# --- HANDLERS ---
@production_handler
@rate_limit("heavy")
async def video_downloader_menu(update: Update, context: CT) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    markup = kb.get_video_platform_keyboard(lang)
    text = TEXTS["video_downloader_menu_prompt"][lang]

    if update.callback_query:
        msg = update.callback_query.message
        if msg.photo or msg.video or msg.document or msg.audio or msg.voice:
            try:
                await msg.delete()
            except:
                pass
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)
        else:
            await update.callback_query.message.edit_text(text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)

    await state.set_state(user_id, "video_menu", {})


async def set_video_platform(update: Update, context: CT, platform: str):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await state.clear_user_states(user_id)

    # Format Selection Inline
    label_map = {
        "tr": {"vid": "🎥 Video", "aud": "🎵 Ses (MP3)", "back": "🔙 Geri"},
        "en": {"vid": "🎥 Video", "aud": "🎵 Audio (MP3)", "back": "🔙 Back"},
        "ru": {"vid": "🎥 Видео", "aud": "🎵 Аудио (MP3)", "back": "🔙 Назад"},
    }
    tx = label_map.get(lang, label_map["en"])

    markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tx["vid"], callback_data=f"VID:FMT:video:{platform}")],
            [InlineKeyboardButton(tx["aud"], callback_data=f"VID:FMT:audio:{platform}")],
            [InlineKeyboardButton(tx["back"], callback_data=callbacks.TOOL_VIDEO)],
        ]
    )

    text = TEXTS["format_selection_prompt"][lang]
    msg = await update.callback_query.message.edit_text(text, reply_markup=markup)
    message_id = getattr(msg, "message_id", update.callback_query.message.message_id)

    await state.set_state(user_id, state.WAITING_FOR_FORMAT_SELECTION, {"platform": platform, "message_id": message_id})


async def set_download_format(update: Update, context: CT, fmt: str, platform: str):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await state.clear_user_states(user_id)

    platform_names = {"tiktok": "TikTok", "twitter": "Twitter/X", "instagram": "Instagram"}
    p_name = platform_names.get(platform, platform)

    text = TEXTS["video_downloader_prompt_link"][lang].format(platform=p_name)
    markup = kb.get_back_keyboard(lang, callbacks.TOOL_VIDEO)

    await update.callback_query.answer()
    msg = await update.callback_query.message.edit_text(text, reply_markup=markup)
    message_id = getattr(msg, "message_id", update.callback_query.message.message_id)

    await state.set_state(
        user_id, state.WAITING_FOR_VIDEO_LINK, {"platform": platform, "format": fmt, "message_id": message_id}
    )


async def download_and_send_media(update: Update, context: CT) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    data = await state.get_data(user_id)
    if not data:
        return

    platform = data.get("platform")
    fmt = data.get("format", "video")
    url = update.message.text.strip()

    # cleanup input
    try:
        await update.message.delete()
    except:
        pass

    if not is_valid_video_url(url, platform):
        await update.message.reply_text(TEXTS["video_invalid_link"][lang].format(platform=platform))
        return

    # cleanup prompt
    await cleanup_context(context, user_id)

    status_msg = await update.message.reply_text(
        "⏳ " + (TEXTS["audio_downloading"][lang] if fmt == "audio" else TEXTS["video_downloading"][lang])
    )

    workspace = create_download_workspace(user_id)
    output_template = get_output_template(workspace)
    downloaded_file = None

    try:
        import yt_dlp

        ydl_opts = {
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
        }

        if fmt == "audio":
            ydl_opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
                    ],
                }
            )
        else:
            ydl_opts.update({"format": "best[filesize<50M]/best"})

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if fmt == "audio":
                    return str(workspace / "media.mp3")
                return ydl.prepare_filename(info)

        downloaded_file = await asyncio.to_thread(download)

        # File checks
        if not os.path.exists(downloaded_file):
            for ext in [".mp3", ".mp4", ".webm", ".m4a"]:
                candidate = workspace / f"media{ext}"
                if candidate.exists():
                    downloaded_file = str(candidate)
                    break

        if not os.path.exists(downloaded_file):
            await status_msg.edit_text("Error: File not found")
            return

        with open(downloaded_file, "rb") as f:
            if fmt == "audio":
                await update.message.reply_audio(
                    f,
                    caption=TEXTS["audio_download_success"][lang],
                    reply_markup=kb.get_back_keyboard(lang, callbacks.TOOL_VIDEO),
                )
            else:
                await update.message.reply_video(
                    f,
                    caption=TEXTS["video_download_success"][lang],
                    reply_markup=kb.get_back_keyboard(lang, callbacks.TOOL_VIDEO),
                )

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text("Download Error")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    await state.clear_user_states(user_id)


# --- ROUTER ---
async def handle_video_callback(update: Update, context: CT):
    query = update.callback_query
    data = query.data

    if data == callbacks.TOOL_VIDEO:
        await video_downloader_menu(update, context)
    elif data == callbacks.VIDEO_TIKTOK:
        await set_video_platform(update, context, "tiktok")
    elif data == callbacks.VIDEO_TWITTER:
        await set_video_platform(update, context, "twitter")
    elif data == callbacks.VIDEO_INSTAGRAM:
        await set_video_platform(update, context, "instagram")
    elif data.startswith("VID:FMT:"):
        # VID:FMT:format:platform
        parts = data.split(":")
        await set_download_format(update, context, parts[2], parts[3])


# --- SETUP ---
def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button, router

    app.add_handler(CommandHandler("video", video_downloader_menu))
    app.add_handler(CallbackQueryHandler(handle_video_callback, pattern=r"^(VID:|TOOL:VIDEO)"))

    router.register(state.WAITING_FOR_VIDEO_LINK, download_and_send_media)

    register_button("video_main_button", video_downloader_menu)
    logger.info("✅ Video module loaded (Inline)")
