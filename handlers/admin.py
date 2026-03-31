"""
Admin Panel Handler for ViraBot
Sadece ADMIN_IDS listesindeki kullanıcılar erişebilir.
"""

import asyncio
import html
import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db

logger = logging.getLogger(__name__)
import pytz

import state
from config import ADMIN_IDS, TIMEZONE
from errors import get_error_message
from utils import get_main_keyboard_markup, is_back_button
from utils.middleware import production_handler


def is_admin(user_id: int) -> bool:
    """Kullanıcının admin olup olmadığını kontrol eder"""
    return user_id in ADMIN_IDS


def get_admin_keyboard():
    """Admin menü klavyesi (Reply Keyboard)"""
    keyboard = [["📊 İstatistikler", "👥 Kullanıcı Listesi"], ["📢 Duyuru Gönder"], ["◀️ Geri"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


@production_handler
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin paneli ana komutu"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Bu komuta erişim yetkiniz yok.")
        return

    # Clean up command/button click
    try:
        await update.message.delete()
    except Exception as e:
        logger.debug(f"Admin command delete error: {e}")

    # State başlat
    await state.clear_user_states(user_id)
    await state.set_state(user_id, state.ADMIN_MENU_ACTIVE)

    # Debug log
    logger.info(f"Admin panel opened for user {user_id}, state set to: {state.ADMIN_MENU_ACTIVE}")

    await update.message.reply_text(
        "🔧 <b>Admin Paneli</b>\n\nBir işlem seçin:", reply_markup=get_admin_keyboard(), parse_mode="HTML"
    )


@production_handler
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin paneli mesaj handler'ı (Reply Keyboard)"""
    user_id = update.effective_user.id

    if not await state.check_state(user_id, state.ADMIN_MENU_ACTIVE):
        return False

    if not is_admin(user_id):
        return False

    text = update.message.text.strip()
    # Debug log
    logger.info(f"Admin Action: User {user_id} sent '{text}'")

    # Cleanup user message
    try:
        await update.message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete admin message: {e}")

    # Geri butonu
    if is_back_button(text):
        await state.clear_user_states(user_id)
        lang = await db.get_user_lang(user_id)
        await update.message.reply_text("🏠 Ana menüye döndünüz.", reply_markup=get_main_keyboard_markup(lang, user_id))
        return True

    # İstatistikler
    if "İstatistik" in text:
        await show_stats_reply(update, context)
        return True

    # Kullanıcı Listesi
    if "Kullanıcı" in text:
        await show_users_reply(update, context)
        return True

    # Duyuru Gönder
    if "Duyuru" in text:
        await start_broadcast_reply(update, context)
        return True

    return False


@production_handler
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel callback handler"""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ Yetkiniz yok!", show_alert=True)
        return

    await query.answer()

    if query.data == "admin_stats":
        await show_stats(query, context)
    elif query.data == "admin_broadcast":
        await start_broadcast(query, context)
    elif query.data == "admin_users":
        await show_users(query, context)
    elif query.data == "admin_exit_to_menu":
        # Admin panelini kapat ve ana menüye dön
        user_id = query.from_user.id
        lang = await db.get_user_lang(user_id)
        await query.delete_message()
        await query.message.chat.send_message(
            "🏠 Ana menüye döndünüz.", reply_markup=get_main_keyboard_markup(lang, user_id)
        )
    elif query.data == "admin_close":
        await query.delete_message()
    elif query.data == "admin_back":
        await query.edit_message_text(
            "🔧 <b>Admin Paneli</b>\n\nBir işlem seçin:", reply_markup=get_admin_keyboard(), parse_mode="HTML"
        )


async def show_stats(query, context):
    """İstatistikleri göster"""
    try:
        # Kullanıcı sayısı
        users = await asyncio.to_thread(db.get_all_users_count)
        notes = await asyncio.to_thread(db.get_all_notes_count)
        reminders = await asyncio.to_thread(db.get_all_reminders_count)

        # AI kullanım istatistikleri (Veritabanından)
        from datetime import date

        today_str = date.today().isoformat()
        ai_stats = await asyncio.to_thread(db.get_ai_total_stats, today_str)

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

        stats_text = f"""📊 *Bot İstatistikleri*

👥 Toplam Kullanıcı: *{users}*
📝 Toplam Not: *{notes}*
⏰ Aktif Hatırlatıcı: *{reminders}*

🤖 *AI Kullanımı (Bugün)*
💬 Mesaj: *{ai_stats["total_messages"]}*
👤 Aktif Kullanıcı: *{ai_stats["unique_users"]}*

🕐 Güncelleme: {now}
"""
        keyboard = [[InlineKeyboardButton("◀️ Geri", callback_data="admin_back")]]
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_stats: {e}", exc_info=True)
        await query.edit_message_text(get_error_message("generic_error", "tr"))


async def start_broadcast(query, context):
    """Duyuru gönderme modunu başlat"""
    context.user_data["admin_broadcast"] = True

    # Inline mesajı sil ve yeni mesaj gönder (mesaj ID'sini sakla)
    await query.delete_message()

    # Reply Keyboard ile Geri butonu
    reply_keyboard = ReplyKeyboardMarkup([["🔙 Admin Paneli"]], resize_keyboard=True, one_time_keyboard=True)

    broadcast_msg = await query.message.chat.send_message(
        "📢 <b>Duyuru Gönder</b>\n\n"
        "Tüm kullanıcılara göndermek istediğiniz mesajı yazın.\n"
        "İptal etmek için aşağıdaki butona basın.",
        reply_markup=reply_keyboard,
        parse_mode="HTML",
    )
    # Mesaj ID'sini sakla (sonra silmek için)
    context.user_data["broadcast_prompt_msg_id"] = broadcast_msg.message_id


@production_handler
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Duyuru mesajını işle ve gönder"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        return False

    if not context.user_data.get("admin_broadcast"):
        return False

    message = update.message.text.strip()

    # Geri butonuna basıldıysa iptal et
    if is_back_button(message):
        context.user_data["admin_broadcast"] = False
        # Prompt mesajını sil
        prompt_msg_id = context.user_data.pop("broadcast_prompt_msg_id", None)
        if prompt_msg_id:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_msg_id)
            except Exception as e:
                logger.debug(f"Failed to delete prompt message: {e}")
        # Admin menüsüne dön (Ana menü yerine)
        await state.clear_user_states(user_id)
        await state.set_state(user_id, state.ADMIN_MENU_ACTIVE)
        await update.message.reply_text(
            "🔧 <b>Admin Paneli</b>\n\nBir işlem seçin:", reply_markup=get_admin_keyboard(), parse_mode="HTML"
        )
        return True

    context.user_data["admin_broadcast"] = False

    # Prompt mesajını sil
    prompt_msg_id = context.user_data.pop("broadcast_prompt_msg_id", None)
    if prompt_msg_id:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_msg_id)
        except Exception as e:
            logger.debug(f"Failed to delete prompt message (2): {e}")

    # Durum mesajı
    status_msg = await update.message.reply_text("📤 Duyuru gönderiliyor...")

    try:
        # ASYNC BROADCAST TASK
        async def broadcast_task(users, message_text):
            sent = 0
            failed = 0
            for uid in users:
                try:
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"📢 <b>Geliştirici Duyurusu</b>\n\n{html.escape(message_text)}\n\n<i>— ViraBot Geliştiricisi</i>",
                        parse_mode="HTML",
                    )
                    sent += 1
                except Exception:  # Broadcast failures are expected (blocked users, etc.)
                    failed += 1
                await asyncio.sleep(0.05)

            try:
                await status_msg.edit_text(
                    f"✅ <b>Duyuru Tamamlandı</b>\n\n📤 Gönderilen: {sent}\n❌ Başarısız: {failed}",
                    parse_mode="HTML",
                    reply_markup=None,
                )
            except Exception as e:
                logger.debug(f"Failed to edit status message: {e}")

        users = await asyncio.to_thread(db.get_all_user_ids)
        _task = asyncio.create_task(broadcast_task(users, message))

        # Don't wait, return to menu immediately
        await update.message.reply_text("⏳ Duyuru işlemi arka planda başlatıldı.")

        # Ana menüye dön
        lang = await db.get_user_lang(user_id)
        await update.message.reply_text("🏠 Ana menüye döndünüz.", reply_markup=get_main_keyboard_markup(lang, user_id))
    except Exception as e:
        logger.error(f"Broadcast error: {e}", exc_info=True)
        await status_msg.edit_text(get_error_message("generic_error", "tr"))

    return True


async def show_users(query, context):
    """Son kullanıcıları listele"""
    try:
        users = await asyncio.to_thread(db.get_recent_users, 10)

        if not users:
            users_text = "👥 Henüz kullanıcı yok."
        else:
            lines = ["👥 *Son 10 Kullanıcı*\n"]
            for i, user in enumerate(users, 1):
                # UserModel objects have attributes, not dict keys
                uid = getattr(user, "user_id", "N/A")
                lang = getattr(user, "language", "?")
                lines.append(f"{i}. `{uid}` ({lang})")
            users_text = "\n".join(lines)

        keyboard = [[InlineKeyboardButton("◀️ Geri", callback_data="admin_back")]]
        await query.edit_message_text(users_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_users: {e}", exc_info=True)
        await query.edit_message_text(get_error_message("generic_error", "tr"))


# --- REPLY KEYBOARD BASED HELPERS ---


async def show_stats_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """İstatistikleri göster (Reply Keyboard için)"""
    try:
        users = await asyncio.to_thread(db.get_all_users_count)
        notes = await asyncio.to_thread(db.get_all_notes_count)
        reminders = await asyncio.to_thread(db.get_all_reminders_count)

        # AI kullanım istatistikleri (Veritabanından) - show_stats ile aynı
        from datetime import date

        today_str = date.today().isoformat()
        ai_stats = await asyncio.to_thread(db.get_ai_total_stats, today_str)

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz).strftime("%d.%m.%Y %H:%M")

        stats_text = f"""📊 <b>Bot İstatistikleri</b>

👥 Toplam Kullanıcı: <b>{users}</b>
📝 Toplam Not: <b>{notes}</b>
⏰ Aktif Hatırlatıcı: <b>{reminders}</b>

🤖 <b>AI Kullanımı (Bugün)</b>
💬 Mesaj: <b>{ai_stats["total_messages"]}</b>
👤 Aktif Kullanıcı: <b>{ai_stats["unique_users"]}</b>

🕐 Güncelleme: {now}
"""
        await update.message.reply_text(stats_text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    except Exception as e:
        logger.error(f"Error in show_stats_reply: {e}", exc_info=True)
        await update.message.reply_text(get_error_message("generic_error", "tr"))


async def show_users_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Son kullanıcıları listele (Reply Keyboard için)"""
    try:
        users = await asyncio.to_thread(db.get_recent_users, 10)

        if not users:
            users_text = "👥 Henüz kullanıcı yok."
        else:
            lines = ["👥 <b>Son 10 Kullanıcı</b>\n"]
            for i, user in enumerate(users, 1):
                # UserModel objects have attributes, not dict keys
                uid = getattr(user, "user_id", "N/A")
                lang = getattr(user, "language", "?")
                lines.append(f"{i}. <code>{uid}</code> ({lang})")
            users_text = "\n".join(lines)

        await update.message.reply_text(users_text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    except Exception as e:
        logger.error(f"Error in show_users_reply: {e}", exc_info=True)
        await update.message.reply_text(get_error_message("generic_error", "tr"))


async def start_broadcast_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Duyuru gönderme modunu başlat (Reply Keyboard için)"""
    user_id = update.effective_user.id
    context.user_data["admin_broadcast"] = True
    await state.clear_user_states(user_id)  # Admin menüsünden çık

    reply_keyboard = ReplyKeyboardMarkup([["🔙 Admin Paneli"]], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "📢 <b>Duyuru Gönder</b>\n\n"
        "Tüm kullanıcılara göndermek istediğiniz mesajı yazın.\n"
        "İptal etmek için aşağıdaki butona basın.",
        reply_markup=reply_keyboard,
        parse_mode="HTML",
    )


# --- MODULAR SETUP ---
def setup(app):
    """Register all handlers for this module."""
    from telegram.ext import CallbackQueryHandler, CommandHandler

    import state
    from core.router import register_button, router

    # 1. Command Handlers
    app.add_handler(CommandHandler("admin", admin_command))

    # 2. Callback Handlers
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin_"))

    # 3. State Handlers (Router)
    router.register(state.ADMIN_MENU_ACTIVE, handle_admin_message)

    # 4. Buttons
    register_button("admin_panel_button", admin_command)

    logger.info("✅ Admin module loaded")
