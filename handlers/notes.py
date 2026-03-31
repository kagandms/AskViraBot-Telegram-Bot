import asyncio
import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
import state
from errors import get_error_message
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils import inline_keyboards as kb
from utils.middleware import production_handler

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
MAX_NOTE_LENGTH = 2000


# --- NOTLAR MENÜSÜ ---
@production_handler
async def notes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Get existing states to safely clear current prompt without deleting it visually if we're editing
    state_data = await state.get_data(user_id)
    if state_data and "message_id" in state_data:
        # Don't delete the message we are currently looking at and trying to edit backward from!
        # Just clear the ID reference so cleanup_context doesn't delete it
        await state.update_data(user_id, {"message_id": None})

    # Cleanup any OTHER floating messages
    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    text = TEXTS["notes_menu_prompt"][lang]
    markup = kb.get_notes_keyboard(lang)

    if update.callback_query:
        await update.callback_query.message.edit_text(text=text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text=text, reply_markup=markup)


# --- NOT EKLEME ---
async def prompt_new_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    await state.clear_user_states(user_id)

    # Inline Input Prompt
    prompt_text = TEXTS["prompt_new_note"][lang]
    back_kb = kb.get_back_keyboard(lang, callbacks.MENU_NOTES)

    if update.callback_query:
        msg = await update.callback_query.message.edit_text(prompt_text, reply_markup=back_kb)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        msg = await update.message.reply_text(prompt_text, reply_markup=back_kb)

    await state.set_state(user_id, state.WAITING_FOR_NEW_NOTE_INPUT, {"message_id": msg.message_id})


@production_handler
async def handle_new_note_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    text = update.message.text

    # Check length
    if len(text) > MAX_NOTE_LENGTH:
        err = {
            "tr": f"⚠️ Not çok uzun. Maksimum {MAX_NOTE_LENGTH} karakter.",
            "en": f"⚠️ Note too long. Max {MAX_NOTE_LENGTH} chars.",
            "ru": f"⚠️ Заметка слишком длинная. Макс {MAX_NOTE_LENGTH} симв.",
        }
        await update.message.reply_text(err.get(lang, err["en"]))
        return

    # Cleanup previous context (the prompt message)
    await cleanup_context(context, user_id)

    # Add note
    saved = await asyncio.to_thread(db.add_note, user_id, text)
    if not saved:
        await state.clear_user_states(user_id)
        await update.message.reply_text(
            get_error_message("database_error", lang), reply_markup=kb.get_notes_keyboard(lang)
        )
        return

    await state.clear_user_states(user_id)

    # Delete input message if possible to keep chat clean
    try:
        await update.message.delete()
    except:
        pass

    success_text = TEXTS["note_saved"][lang] + "\n\n" + html.escape(text)
    markup = kb.get_notes_keyboard(lang)
    await update.message.reply_text(success_text, reply_markup=markup, parse_mode="HTML")


# --- NOTLARI GÖSTER ---
async def shownotes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    notes = await asyncio.to_thread(db.get_notes, user_id)

    if not notes:
        text = TEXTS["no_notes"][lang]
    else:
        text = TEXTS["notes_header"][lang] + "\n\n"
        for i, note in enumerate(notes, 1):
            text += f"<b>{i}.</b> {html.escape(note)}\n"

    markup = kb.get_back_keyboard(lang, callbacks.MENU_NOTES)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


# --- NOT SİLME (Pagination) ---
async def deletenotes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Get page from state
    state_data = await state.get_data(user_id)
    if not state_data:
        state_data = {}
    page = state_data.get("page", 0)

    notes = await asyncio.to_thread(db.get_notes, user_id)

    if not notes:
        if update.callback_query:
            await update.callback_query.answer(TEXTS["no_notes"][lang])
            return
        else:
            await update.message.reply_text(TEXTS["no_notes"][lang])
            return

    # Pagination
    PER_PAGE = 5
    start = page * PER_PAGE
    end = start + PER_PAGE
    current_notes = notes[start:end]

    keyboard = []
    for i, note in enumerate(current_notes):
        idx = start + i
        preview = note[:20] + "..." if len(note) > 20 else note
        btn_text = f"🗑 {idx + 1}. {preview}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"NOTE:DELETE_EXEC:{idx}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"NOTE:DELETE_PAGE:{page - 1}"))
    if end < len(notes):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"NOTE:DELETE_PAGE:{page + 1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.MENU_NOTES)])
    markup = InlineKeyboardMarkup(keyboard)

    text = TEXTS["prompt_select_note_to_delete"][lang]

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=markup)
    else:
        try:
            if update.message:
                await update.message.delete()
        except:
            pass
        await update.message.reply_text(text, reply_markup=markup)

    await state.set_state(user_id, state.DELETING_NOTES, {"page": page})


async def delete_note_exec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    lang = await db.get_user_lang(user_id)

    idx = int(query.data.split(":")[-1])

    notes = await asyncio.to_thread(db.get_notes, user_id)
    if idx < len(notes):
        deleted = await asyncio.to_thread(db.delete_note, user_id, idx + 1)
        if deleted:
            await query.answer(TEXTS["note_deleted"][lang])
        else:
            await query.answer(get_error_message("database_error", lang), show_alert=True)
    else:
        await query.answer(get_error_message("not_found", lang), show_alert=True)

    await deletenotes_menu(update, context)


async def delete_note_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    page = int(update.callback_query.data.split(":")[-1])
    user_id = update.effective_user.id
    await state.set_state(user_id, state.DELETING_NOTES, {"page": page})
    await deletenotes_menu(update, context)


# --- NOT DÜZENLEME (List then Edit) ---
async def edit_notes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    notes = await asyncio.to_thread(db.get_notes, user_id)
    if not notes:
        await update.callback_query.answer(TEXTS["no_notes"][lang])
        return

    keyboard = []
    for i, note in enumerate(notes):
        preview = note[:20] + "..." if len(note) > 20 else note
        btn_text = f"✏️ {i + 1}. {preview}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"NOTE:EDIT_SEL:{i}")])

    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.MENU_NOTES)])
    markup = InlineKeyboardMarkup(keyboard)

    text = TEXTS["edit_notes_menu_prompt"][lang]
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(text, reply_markup=markup)


async def edit_note_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    lang = await db.get_user_lang(user_id)
    idx = int(query.data.split(":")[-1])

    notes = await asyncio.to_thread(db.get_notes, user_id)
    if idx >= len(notes):
        await query.answer(get_error_message("not_found", lang), show_alert=True)
        return

    current_note = notes[idx]

    text_dict = {
        "tr": f"✏️ <b>Mevcut Not:</b>\n<code>{html.escape(current_note)}</code>\n\n👇 Yeni metni girin:",
        "en": f"✏️ <b>Current:</b>\n<code>{html.escape(current_note)}</code>\n\n👇 Enter new text:",
        "ru": f"✏️ <b>Текущая:</b>\n<code>{html.escape(current_note)}</code>\n\n👇 Введите новый текст:",
    }
    text = text_dict.get(lang, text_dict["en"])

    keyboard = []
    keyboard.append([InlineKeyboardButton(TEXTS["back_button_inline"][lang], callback_data=callbacks.NOTE_EDIT_MENU)])
    markup = InlineKeyboardMarkup(keyboard)

    await query.answer()
    msg = await query.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

    await state.set_state(user_id, state.WAITING_FOR_EDIT_NOTE_INPUT, {"idx": idx, "message_id": msg.message_id})


@production_handler
async def handle_edit_note_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)
    new_text = update.message.text

    state_data = await state.get_data(user_id)
    idx = state_data.get("idx")

    if idx is not None:
        updated = await asyncio.to_thread(db.update_note, user_id, int(idx) + 1, new_text)
        if not updated:
            await state.clear_user_states(user_id)
            await update.message.reply_text(
                get_error_message("database_error", lang), reply_markup=kb.get_notes_keyboard(lang)
            )
            return

        # Cleanup edit prompt message
        await cleanup_context(context, user_id)

        try:
            await update.message.delete()
        except:
            pass

        await update.message.reply_text(TEXTS["note_updated"][lang], reply_markup=kb.get_notes_keyboard(lang))
    else:
        await update.message.reply_text(get_error_message("session_expired", lang))

    await state.clear_user_states(user_id)


# --- ROUTER ---
async def handle_notes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if data == callbacks.NOTE_ADD:
        await prompt_new_note(update, context)
    elif data == callbacks.NOTE_LIST:
        await shownotes_command(update, context)
    elif data == callbacks.NOTE_EDIT_MENU:
        await edit_notes_menu(update, context)
    elif data == callbacks.NOTE_DELETE_MENU:
        await deletenotes_menu(update, context)
    elif data.startswith("NOTE:DELETE_EXEC:"):
        await delete_note_exec(update, context)
    elif data.startswith("NOTE:DELETE_PAGE:"):
        await delete_note_page(update, context)
    elif data.startswith("NOTE:EDIT_SEL:"):
        await edit_note_select(update, context)
    elif data == callbacks.MENU_NOTES or data == callbacks.TOOL_NOTES:
        await notes_menu(update, context)


# --- MODULAR SETUP ---
def setup(app):
    from core.router import register_button, router

    app.add_handler(CommandHandler("notes", notes_menu))
    app.add_handler(CommandHandler("addnote", prompt_new_note))
    app.add_handler(CommandHandler("shownotes", shownotes_command))

    # Callback Handler
    app.add_handler(CallbackQueryHandler(handle_notes_callback, pattern=r"^(NOTE:|TOOL:NOTES|MENU:NOTES)"))

    router.register(state.WAITING_FOR_NEW_NOTE_INPUT, handle_new_note_input)
    router.register(state.WAITING_FOR_EDIT_NOTE_INPUT, handle_edit_note_input)
    router.register(state.DELETING_NOTES, deletenotes_menu)

    register_button("notes_main_button", notes_menu)

    logger.info("✅ Notes module loaded")
