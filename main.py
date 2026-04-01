from __future__ import annotations

import asyncio
import hashlib
import os
from threading import Event, Thread

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters

import database as db
import state

# Modülleri içe aktar
from config import BOT_TOKEN
from core.loader import load_handlers

# Handler'ları içe aktar (Sadece handle_buttons_logic içinde kullanılanlar)
from handlers import admin, general
from keep_alive import (
    clear_bot_runtime,
    keep_alive,
    mark_bot_failed,
    mark_bot_ready,
    mark_bot_starting,
    register_bot_runtime,
    run_http_server,
)

# --- LOGLAMA YAPILANDIRMASI ---
from logger import get_logger, setup_logging
from rate_limiter import get_remaining_cooldown, is_rate_limited
from texts import BUTTON_MAPPINGS, TEXTS

setup_logging()
logger = get_logger(__name__)
WEBHOOK_PATH = "/telegram-webhook"


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


async def on_startup(application: Application) -> None:
    logger.info("Bot başlatılıyor... Bekleyen hatırlatıcılar kontrol ediliyor.")
    from services.cache_service import init_redis

    init_redis()
    # Reminder modules are likely loaded now, so we can access them via global state or import
    # But dynamic import is safer if we want to be clean, or just keep import at top
    from handlers import reminders

    await reminders.start_pending_reminders(application)
    mark_bot_ready()


async def on_shutdown(application: Application) -> None:
    logger.info("Bot kapatılıyor... HTTP session temizleniyor.")
    from handlers import metro

    await metro.close_http_session()
    clear_bot_runtime()


def build_application() -> Application:
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).post_shutdown(on_shutdown).build()

    load_handlers(application)

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND) | filters.Document.ALL | filters.PHOTO, handle_buttons)
    )
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    return application


def build_webhook_secret() -> str:
    return hashlib.sha256(BOT_TOKEN.encode("utf-8")).hexdigest()


class WebhookRuntime:
    def __init__(self, application: Application, webhook_url: str, secret_token: str) -> None:
        self._application = application
        self._webhook_url = webhook_url
        self._secret_token = secret_token
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: Thread | None = None
        self._ready_event = Event()
        self._startup_error: Exception | None = None
        self._started = False

    def start(self) -> None:
        mark_bot_starting(mode="webhook", webhook_path=WEBHOOK_PATH, webhook_url=self._webhook_url)
        self._thread = Thread(target=self._run, name="telegram-webhook-runtime", daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=30)

        if self._startup_error:
            raise RuntimeError("Webhook runtime failed to start.") from self._startup_error

        if not self._started:
            raise RuntimeError("Webhook runtime startup timed out.")

    def stop(self) -> None:
        if not self._loop or not self._thread:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=10)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._async_start())
            self._started = True
            self._ready_event.set()
            loop.run_forever()
        except Exception as e:
            self._startup_error = e
            mark_bot_failed(str(e))
            self._ready_event.set()
        finally:
            if self._started:
                loop.run_until_complete(self._async_stop())
            loop.close()

    async def _async_start(self) -> None:
        await self._application.initialize()
        if not self._loop:
            raise RuntimeError("Webhook loop was not initialized.")

        register_bot_runtime(
            application=self._application,
            loop=self._loop,
            secret_token=self._secret_token,
        )

        if self._application.post_init:
            await self._application.post_init(self._application)

        await self._application.start()
        await self._application.bot.set_webhook(url=self._webhook_url, secret_token=self._secret_token)
        logger.info(f"✅ Webhook registered: {self._webhook_url}")

    async def _async_stop(self) -> None:
        try:
            await self._application.bot.delete_webhook()
        except Exception as e:
            logger.warning(f"Webhook cleanup failed: {e}")

        if self._application.running:
            await self._application.stop()

            if self._application.post_stop:
                await self._application.post_stop(self._application)

        await self._application.shutdown()

        if self._application.post_shutdown:
            await self._application.post_shutdown(self._application)


def main() -> None:
    render_external_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    application = build_application()

    if render_external_url:
        webhook_url = f"{render_external_url}{WEBHOOK_PATH}"
        runtime = WebhookRuntime(application, webhook_url, build_webhook_secret())
        logger.info("🚀 PRODUCTION MODE - Webhook + Flask")
        logger.info(f"🌐 Telegram webhook target: {webhook_url}")
        runtime.start()

        try:
            run_http_server()
        finally:
            runtime.stop()
        return

    logger.info("📡 POLLING MODE (No RENDER_EXTERNAL_URL found)")
    mark_bot_starting(mode="polling")
    keep_alive()
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"🔥 FATAL ERROR: Bot crashed during startup: {e}", exc_info=True)
        # Keep process alive briefly to ensure logs are flushed if needed, or just exit with error code
        import sys

        sys.exit(1)
