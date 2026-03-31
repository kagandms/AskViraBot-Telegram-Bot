import html
import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)
import database as db
import state
from config import BOT_NAME
from core.router import register_button
from texts import TEXTS
from utils import attach_user, callbacks, cleanup_context, handle_errors
from utils import inline_keyboards as kb
from utils.middleware import production_handler


@production_handler
@handle_errors
@attach_user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, user=None) -> None:
    """Bot başlatma komutu."""
    # user is injected by @attach_user
    await state.clear_user_states(user.user_id)
    # Direct access to language from user model
    lang = await db.get_user_lang(user.user_id)

    await update.message.reply_text(
        TEXTS["start"][lang].format(bot_name=html.escape(BOT_NAME)),
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard(lang),
    )


@production_handler
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ana menüyü gösterir. Hem komut hem de callback (geri tuşu) ile çalışır."""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Cleanup
    await cleanup_context(context, user_id)

    # Eğer callback query (buton) üzerinden geldiyse
    if update.callback_query:
        await update.callback_query.answer()
        # Mesajı düzenle
        try:
            await update.callback_query.message.edit_text(
                text=TEXTS["menu_prompt"][lang], reply_markup=kb.get_main_keyboard(lang)
            )
        except Exception as e:
            # Düzenleme başarısızsa (örn. içerik aynı) yeni mesaj at
            logger.debug(f"Menu edit failed: {e}")
            await context.bot.send_message(
                chat_id=user_id, text=TEXTS["menu_prompt"][lang], reply_markup=kb.get_main_keyboard(lang)
            )
    # Normal mesaj (/menu) üzerinden geldiyse
    else:
        # Eski mesajı silmeye çalışalım
        try:
            if update.message:
                await update.message.delete()
        except:
            pass

        await update.message.reply_text(TEXTS["menu_prompt"][lang], reply_markup=kb.get_main_keyboard(lang))

    await state.clear_user_states(user_id)


@production_handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tüm komutları ve özellikleri listeler"""
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    help_texts = {
        "tr": """📚 *{bot_name} Nasıl Kullanılır?*

🏠 *Ana Menü*
Tüm özelliklere menü butonlarından kolayca ulaşabilirsin!

━━━━━━━━━━━━━━━━━━━━

📝 *Notlar*
• ➕ Not Ekle – Yeni not kaydet
• 📋 Notları Göster – Tüm notlarını listele
• ✏️ Not Düzenle – Mevcut notu güncelle
• 🗑️ Not Sil – İstemediğin notu kaldır

━━━━━━━━━━━━━━━━━━━━

⏰ *Hatırlatıcılar*
• Belirli saat ve tarihte hatırlatma kur
• Örnek: `14:30 toplantı` veya `10:00 2025-12-31 yılbaşı`

━━━━━━━━━━━━━━━━━━━━

🎮 *Oyun Odası*
• ❌⭕ XOX – 3 zorluk seviyesi
• 🎲 Zar – Rastgele zar at
• 🪙 Yazı Tura – Şansını dene
• 🪨📄✂️ Taş-Kağıt-Makas – Bota karşı oyna

━━━━━━━━━━━━━━━━━━━━

🛠 *Araçlar*
• 📷 QR Kod – Metin/link'ten QR oluştur
• 📄 PDF Dönüştürücü – Metin, resim veya belgeyi PDF yap
• ☀️ Hava Durumu – 9 şehir + *5 günlük tahmin*
• 📥 Video İndir – TikTok, Twitter/X, Instagram
• 🚇 Canlı Metro İstanbul – Gerçek zamanlı sefer saatleri

━━━━━━━━━━━━━━━━━━━━

🤖 *AI Asistan (Beta)*
• Yapay zeka destekli sohbet
• Günlük 30 mesaj hakkı
• Her türlü soruyu sorabilirsin!

━━━━━━━━━━━━━━━━━━━━

⚙️ *Ayarlar*
• 🌐 Dil Değiştir – TR / EN / RU

💡 *İpucu:* Menü butonlarını kullanarak daha hızlı gezinebilirsin!""",
        "en": """📚 *{bot_name} – How to Use?*

🏠 *Main Menu*
Access all features easily through the menu buttons!

━━━━━━━━━━━━━━━━━━━━

📝 *Notes*
• ➕ Add Note – Save a new note
• 📋 Show Notes – List all your notes
• ✏️ Edit Note – Update an existing note
• 🗑️ Delete Note – Remove unwanted notes

━━━━━━━━━━━━━━━━━━━━

⏰ *Reminders*
• Set reminders for specific time and date
• Example: `14:30 meeting` or `10:00 2025-12-31 new year`

━━━━━━━━━━━━━━━━━━━━

🎮 *Game Room*
• ❌⭕ XOX – 3 difficulty levels
• 🎲 Dice – Roll a random dice
• 🪙 Coinflip – Test your luck
• 🪨📄✂️ Rock-Paper-Scissors – Play against the bot

━━━━━━━━━━━━━━━━━━━━

🛠 *Tools*
• 📷 QR Code – Generate QR from text/link
• 📄 PDF Converter – Convert text, image or document to PDF
• ☀️ Weather – 9 cities + *5-day forecast*
• 📥 Video Download – TikTok, Twitter/X, Instagram
• 🚇 Live Metro Istanbul – Real-time departure schedules

━━━━━━━━━━━━━━━━━━━━

🤖 *AI Assistant (Beta)*
• AI-powered chat assistant
• 30 messages per day
• Ask anything you want!

━━━━━━━━━━━━━━━━━━━━

⚙️ *Settings*
• 🌐 Change Language – TR / EN / RU

💡 *Tip:* Use menu buttons for faster navigation!""",
        "ru": """📚 *{bot_name} – Как использовать?*

🏠 *Главное меню*
Все функции доступны через кнопки меню!

━━━━━━━━━━━━━━━━━━━━

📝 *Заметки*
• ➕ Добавить – Сохранить новую заметку
• 📋 Показать – Список всех заметок
• ✏️ Изменить – Обновить заметку
• 🗑️ Удалить – Удалить ненужные заметки

━━━━━━━━━━━━━━━━━━━━

⏰ *Напоминания*
• Установите напоминание на конкретное время
• Пример: `14:30 встреча` или `10:00 2025-12-31 новый год`

━━━━━━━━━━━━━━━━━━━━

🎮 *Игровая комната*
• ❌⭕ XOX – 3 уровня сложности
• 🎲 Кубик – Бросить случайный кубик
• 🪙 Монета – Испытай удачу
• 🪨📄✂️ Камень-Ножницы-Бумага – Играй против бота

━━━━━━━━━━━━━━━━━━━━

🛠 *Инструменты*
• 📷 QR-код – Создать QR из текста/ссылки
• 📄 PDF Конвертер – Конвертировать в PDF
• ☀️ Погода – 9 городов + *5-дневный прогноз*
• 📥 Скачать видео – TikTok, Twitter/X, Instagram
• 🚇 Метро Стамбул – Расписание в реальном времени

━━━━━━━━━━━━━━━━━━━━

🤖 *AI Ассистент (Бета)*
• Чат с искусственным интеллектом
• 30 сообщений в день
• Спрашивай что угодно!

━━━━━━━━━━━━━━━━━━━━

⚙️ *Настройки*
• 🌐 Сменить язык – TR / EN / RU

💡 *Совет:* Используйте кнопки меню для быстрой навигации!""",
    }

    text = help_texts.get(lang, help_texts["en"]).format(bot_name=html.escape(BOT_NAME))

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text=text, parse_mode="HTML", reply_markup=kb.get_back_keyboard(lang, callbacks.MENU_MAIN)
        )
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(
            text=text, parse_mode="HTML", reply_markup=kb.get_back_keyboard(lang, callbacks.MENU_MAIN)
        )


async def show_language_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dil seçim klavyesini gösterir"""
    text = "🇹🇷 Lütfen bir dil seçin\n🇬🇧 Please select a language\n🇷🇺 Пожалуйста, выберите язык"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=kb.get_language_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=kb.get_language_keyboard())


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline language selection."""
    query = update.callback_query
    data = query.data
    user_id = str(update.effective_user.id)

    lang_map = {callbacks.LANG_TR: "tr", callbacks.LANG_EN: "en", callbacks.LANG_RU: "ru"}

    new_lang = lang_map.get(data)
    if new_lang:
        await db.set_user_lang_db(user_id, new_lang)

        # Confirm selection (Toast notification)
        confirm_text = {
            "tr": "✅ Dil Türkçe olarak ayarlandı",
            "en": "✅ Language set to English",
            "ru": "✅ Язык установлен на Русский",
        }
        await query.answer(confirm_text.get(new_lang, "✅ Language set"))

        # Refresh menu in new language
        await menu_command(update, context)


async def set_language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy command handler for /tr /en /ru"""
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()

    lang_to_set = None
    if "/tr" in text:
        lang_to_set = "tr"
    elif "/en" in text:
        lang_to_set = "en"
    elif "/ru" in text:
        lang_to_set = "ru"

    if lang_to_set:
        await db.set_user_lang_db(user_id, lang_to_set)
        await update.message.reply_text(f"Language set to: {lang_to_set}")
        await menu_command(update, context)


# Legacy text-based language button handler (backward compatibility)
@production_handler
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kullanıcı dilini ayarlar (metin tabanlı butonlar için geriye uyumluluk)."""
    user_id = str(update.effective_user.id)
    await state.clear_user_states(user_id)

    text = update.message.text.lower()
    lang_to_set = None
    if "türkçe" in text:
        lang_to_set = "tr"
    elif "english" in text:
        lang_to_set = "en"
    elif "русский" in text:
        lang_to_set = "ru"
    else:
        command_lang = update.message.text[1:].lower()
        if command_lang in ["tr", "en", "ru"]:
            lang_to_set = command_lang

    if lang_to_set:
        await db.set_user_lang_db(user_id, lang_to_set)
        await update.message.reply_text(TEXTS["language_set"][lang_to_set])
        await menu_command(update, context)


# --- CALLBACK DISPATCHER ---
async def handle_general_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatches general callbacks."""
    query = update.callback_query
    data = query.data

    if data == callbacks.MENU_MAIN:
        await menu_command(update, context)
    elif data == callbacks.MENU_HELP:
        await help_command(update, context)
    elif data == callbacks.MENU_LANGUAGE:
        await show_language_keyboard(update, context)
    elif data.startswith(callbacks.LANG_PREFIX):
        await handle_language_callback(update, context)


# --- MODULAR SETUP ---
def setup(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["tr", "en", "ru"], set_language_command))

    # Callback Handler
    app.add_handler(CallbackQueryHandler(handle_general_callback, pattern=r"^(MENU:MAIN|MENU:HELP|MENU:LANG|LANG:)"))

    # Register Buttons (backward compatibility for text-based routing)
    register_button("menu", menu_command)
    register_button("help_button", help_command)
    register_button("language", show_language_keyboard)

    logger.info("✅ General module loaded")
