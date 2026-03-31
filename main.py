from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

import database as db
import state

# Modülleri içe aktar
from config import BOT_TOKEN
from core.loader import load_handlers

# Handler'ları içe aktar (Sadece handle_buttons_logic içinde kullanılanlar)
from handlers import admin, general
from keep_alive import keep_alive

# --- LOGLAMA YAPILANDIRMASI ---
from logger import get_logger, setup_logging
from rate_limiter import get_remaining_cooldown, is_rate_limited
from texts import BUTTON_MAPPINGS, TEXTS

setup_logging()
logger = get_logger(__name__)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # DB İŞLEMİ: Asenkron yapıldı
    lang = await db.get_user_lang(user_id)
    await update.message.reply_text(TEXTS["unknown_command"][lang])


from core import router


# --- ANA BUTON YÖNETİCİSİ (ROUTER) ---
async def handle_buttons_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # Metin varsa al, yoksa boş string (Dosya/Fotoğraf durumları için)
    text_raw = update.message.text if update.message.text else ""
    # Türkçe İ/i karakterlerini doğru işlemek için turkish_lower kullanılır
    from texts import turkish_lower

    text = turkish_lower(text_raw).strip()
    user_id = update.effective_user.id

    # Genel Rate Limit Kontrolü
    if is_rate_limited(user_id, "general"):
        cooldown = get_remaining_cooldown(user_id, "general")
        lang = await db.get_user_lang(user_id)
        rate_limit_msgs = {
            "tr": f"⏳ Çok fazla istek gönderdiniz. Lütfen {cooldown} saniye bekleyin.",
            "en": f"⏳ Too many requests. Please wait {cooldown} seconds.",
            "ru": f"⏳ Слишком много запросов. Подождите {cooldown} секунд.",
        }
        await update.message.reply_text(rate_limit_msgs.get(lang, rate_limit_msgs["en"]))
        return

    # Admin Broadcast Kontrolü - Özel Durum (State'den bağımsız araya girebilir)
    if await admin.handle_broadcast_message(update, context):
        return

    # *** DİL BUTONLARI - EN ÖNCELİKLİ (State'den bağımsız çalışmalı) ***
    from core.router import LANGUAGE_BUTTONS

    if text and text in LANGUAGE_BUTTONS:
        await state.clear_user_states(user_id)  # State'i temizle
        await general.set_language(update, context)
        return

    # 2. State Kontrolleri - ROUTER ISLEMI
    # Kullanıcının aktif state'ini al
    user_state = await state.get_state(user_id)
    if user_state:
        # Router'a sor: Bu state için bir handler var mı?
        # Varsa çalıştır ve çık.
        handled = await router.dispatch(user_state, update, context)
        if handled:
            return

    # EĞER HİÇBİR STATE'E GİRMEDİYSE VE METİN YOKSA (Beklenmeyen Dosya)
    if not text:
        lang = await db.get_user_lang(user_id)
        msg_warn = {
            "tr": "⚠️ Beklenmeyen dosya. Lütfen önce menüden bir işlem (örn. PDF) seçin.",
            "en": "⚠️ Unexpected file. Please select an action from the menu first.",
            "ru": "⚠️ Неожиданный файл. Сначала выберите действие из меню.",
        }
        await update.message.reply_text(msg_warn.get(lang, msg_warn["en"]))
        return

    # 3. Dinamik Buton Yönlendirme (Router Pattern)
    # Unified import: Everything is now in core.router
    from core.router import LANGUAGE_BUTTONS, button_handlers, format_handlers, video_platform_handlers
    from texts import turkish_lower

    # Lowercase for Turkish character handling
    text_lower = turkish_lower(text)

    # Standart buton eşleşmeleri
    for mapping_key, handler in button_handlers.items():
        if text_lower in BUTTON_MAPPINGS.get(mapping_key, set()):
            await handler(update, context)
            return

    # Video platform butonları
    for mapping_key, handler in video_platform_handlers.items():
        if text_lower in BUTTON_MAPPINGS.get(mapping_key, set()):
            await handler(update, context)
            return

    # Format seçim butonları
    for mapping_key, handler in format_handlers.items():
        if text_lower in BUTTON_MAPPINGS.get(mapping_key, set()):
            await handler(update, context)
            return

    # Hiçbir buton eşleşmedi
    await unknown_command(update, context)


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await handle_buttons_logic(update, context)
    except Exception as e:
        logger.error(f"Error in handle_buttons: {e}", exc_info=True)
        # Hata detayını gizle
        if update.message:
            await update.message.reply_text("⚠️ Bir hata oluştu. Lütfen daha sonra tekrar deneyin.")


async def on_startup(application):
    logger.info("Bot başlatılıyor... Bekleyen hatırlatıcılar kontrol ediliyor.")
    from services.cache_service import init_redis

    init_redis()
    # Reminder modules are likely loaded now, so we can access them via global state or import
    # But dynamic import is safer if we want to be clean, or just keep import at top
    from handlers import reminders

    await reminders.start_pending_reminders(application)


async def on_shutdown(application):
    logger.info("Bot kapatılıyor... HTTP session temizleniyor.")
    from handlers import metro

    await metro.close_http_session()


def main():
    import os

    # Webhook configuration - Render provides RENDER_EXTERNAL_URL automatically
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "")
    PORT = int(os.getenv("PORT", 8080))

    # Build telegram application
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).post_shutdown(on_shutdown).build()

    # --- AUTOMATIC HANDLER LOADING ---
    load_handlers(app)

    # Register Global Message Handler (Fallback for buttons/text)
    # This must be added AFTER module handlers to avoid overriding commands?
    # Actually, CommandHandlers are usually checked first if added first.
    # load_handlers adds commands.
    # We should add MessageHandler LAST.

    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND) | filters.Document.ALL | filters.PHOTO, handle_buttons)
    )
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # --- PRODUCTION MODE (Render) ---
    # Using polling + Flask health check for reliability on free tier
    # Flask runs on PORT for UptimeRobot, bot uses polling for Telegram
    if WEBHOOK_URL:
        logger.info("🚀 PRODUCTION MODE - Polling + Health Check")
        logger.info(f"🌐 Health check on port {PORT}")
        keep_alive()  # Flask server for UptimeRobot
        app.run_polling(drop_pending_updates=True)

    # --- POLLING MODE (Local development) ---
    else:
        logger.info("📡 POLLING MODE (No RENDER_EXTERNAL_URL found)")
        keep_alive()
        app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"🔥 FATAL ERROR: Bot crashed during startup: {e}", exc_info=True)
        # Keep process alive briefly to ensure logs are flushed if needed, or just exit with error code
        import sys

        sys.exit(1)
