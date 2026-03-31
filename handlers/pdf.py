import asyncio
import logging
import os
import uuid

from fpdf import FPDF
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes as CT

import database as db
import state
from config import FONT_PATH
from rate_limiter import rate_limit
from texts import TEXTS
from utils import callbacks, cleanup_context
from utils import inline_keyboards as kb
from utils.middleware import production_handler

logger = logging.getLogger(__name__)


@production_handler
@rate_limit("heavy")
async def pdf_converter_menu(update: Update, context: CT):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    await cleanup_context(context, user_id)
    await state.clear_user_states(user_id)

    text = TEXTS["pdf_converter_menu_prompt"][lang]
    markup = kb.get_pdf_menu_keyboard(lang)

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

    await state.set_state(user_id, "pdf_menu", {})


async def prompt_input(update: Update, context: CT, mode):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    key_map = {"text": "prompt_text_for_pdf", "file": "prompt_file_for_pdf"}
    text = TEXTS[key_map.get(mode, "prompt_file_for_pdf")][lang]

    markup = kb.get_back_keyboard(lang, callbacks.PDF_BACK)

    if update.callback_query:
        await update.callback_query.answer()
        msg = await update.callback_query.message.edit_text(text, reply_markup=markup)
        message_id = getattr(msg, "message_id", update.callback_query.message.message_id)
    else:
        msg = await update.message.reply_text(text, reply_markup=markup)
        message_id = msg.message_id

    await state.set_state(user_id, state.WAITING_FOR_PDF_CONVERSION_INPUT, {"pdf_mode": mode, "message_id": message_id})


async def handle_pdf_callback(update: Update, context: CT):
    query = update.callback_query
    data = query.data

    if data == callbacks.PDF_BACK or data == callbacks.TOOL_PDF:
        await pdf_converter_menu(update, context)
        return

    if data == callbacks.PDF_TEXT:
        await prompt_input(update, context, "text")
    elif data == callbacks.PDF_IMAGE or data == callbacks.PDF_DOC:
        await prompt_input(update, context, "file")


async def handle_pdf_input(update: Update, context: CT):
    user_id = update.effective_user.id
    lang = await db.get_user_lang(user_id)

    # Check if back button (text) was pressed (Legacy support)
    if update.message.text and update.message.text.lower() in ["back", "geri", "назад"]:
        await pdf_converter_menu(update, context)
        return

    # Existing logic
    output_filename = f"document_{user_id}_{uuid.uuid4().hex[:8]}.pdf"
    temp_files = []

    # Cleanup prompt
    await cleanup_context(context, user_id)

    processing_texts = {"tr": "⏳ PDF hazırlanıyor...", "en": "⏳ Preparing...", "ru": "⏳ Подготовка..."}
    proc_msg = await update.message.reply_text(processing_texts.get(lang, "⏳"))

    try:
        pdf = FPDF()
        pdf.add_page()

        if os.path.exists(FONT_PATH):
            pdf.add_font("DejaVu", "", FONT_PATH)
            pdf.set_font("DejaVu", size=12)
        else:
            pdf.set_font("Helvetica", size=12)

        if update.message.text:
            pdf.multi_cell(w=pdf.epw, h=10, text=update.message.text)
            pdf.output(output_filename)
        elif update.message.photo:
            f = await update.message.photo[-1].get_file()
            path = f"temp_img_{user_id}.jpg"
            temp_files.append(path)
            await f.download_to_drive(path)
            pdf.image(path, x=10, y=10, w=190)
            pdf.output(output_filename)
        elif update.message.document:
            doc = update.message.document
            if doc.mime_type == "text/plain":
                path = f"temp_doc_{user_id}.txt"
                temp_files.append(path)
                f = await doc.get_file()
                await f.download_to_drive(path)
                with open(path, encoding="utf-8") as tf:
                    pdf.multi_cell(w=pdf.epw, h=10, text=tf.read())
                pdf.output(output_filename)
            elif doc.mime_type and doc.mime_type.startswith("image/"):
                img_path = f"temp_doc_img_{user_id}"
                temp_files.append(img_path)
                f = await doc.get_file()
                await f.download_to_drive(img_path)

                try:
                    cover = Image.open(img_path)
                    # Convert transparent/PNG to JPG
                    if cover.mode in ("RGBA", "LA") or (cover.mode == "P" and "transparency" in cover.info):
                        bg = Image.new("RGB", cover.size, (255, 255, 255))
                        bg.paste(cover, mask=cover.convert("RGBA").split()[-1])
                        cover = bg

                    jpg_path = img_path + ".jpg"
                    cover.save(jpg_path, "JPEG", quality=90)
                    temp_files.append(jpg_path)
                    pdf.image(jpg_path, x=10, y=10, w=190)
                    pdf.output(output_filename)
                except Exception as e:
                    logger.error(f"Image proc error: {e}")
                    await proc_msg.delete()
                    await update.message.reply_text("Image Error")
                    return
            else:
                await proc_msg.delete()
                await update.message.reply_text(TEXTS["unsupported_file_type"][lang])
                return
        else:
            await proc_msg.delete()
            await update.message.reply_text(TEXTS["unsupported_file_type"][lang])
            return

        await proc_msg.delete()
        with open(output_filename, "rb") as f:
            await update.message.reply_document(f, caption=TEXTS["pdf_conversion_success"][lang])

        # Log usage
        await asyncio.to_thread(db.log_pdf_usage, user_id, "pdf_conv")

    except Exception as e:
        logger.error(f"PDF Error: {e}")
        await proc_msg.delete()
        await update.message.reply_text("Error")
    finally:
        if os.path.exists(output_filename):
            os.remove(output_filename)
        for t in temp_files:
            if os.path.exists(t):
                os.remove(t)

    await state.clear_user_states(user_id)
    # Return to menu
    await pdf_converter_menu(update, context)


def setup(app):
    from telegram.ext import CallbackQueryHandler, CommandHandler

    from core.router import register_button, router

    app.add_handler(CommandHandler("pdfconverter", pdf_converter_menu))
    app.add_handler(CallbackQueryHandler(handle_pdf_callback, pattern=r"^(PDF:|TOOL:PDF)"))
    router.register(state.WAITING_FOR_PDF_CONVERSION_INPUT, handle_pdf_input)
    register_button("pdf_converter_main_button", pdf_converter_menu)
    logger.info("✅ PDF module loaded (Inline)")
