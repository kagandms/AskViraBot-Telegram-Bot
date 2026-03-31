import asyncio
import logging

from texts import TEXTS

logger = logging.getLogger(__name__)


def is_back_button(text: str) -> bool:
    if not text:
        return False

    from texts import BUTTON_MAPPINGS, turkish_lower

    text_lower = turkish_lower(text)

    generic_back = {"geri", "back", "назад", "iptal", "cancel", "отмена"}

    mapped_back = (
        BUTTON_MAPPINGS.get("back_to_main_menu", set())
        | BUTTON_MAPPINGS.get("back_to_tools", set())
        | BUTTON_MAPPINGS.get("back_to_games", set())
    )

    specific_back = {
        "🔙 ana menü",
        "🔙 main menu",
        "🔙 главное меню",
        "🔙 araçlar menüsü",
        "🔙 tools menu",
        "🔙 меню инструментов",
        "🔙 oyun odası",
        "🔙 game room",
        "🔙 игровая комната",
        "🔙 hat listesi",
        "🔙 line list",
        "🔙 список линий",
        "🔙 istasyon listesi",
        "🔙 station list",
        "🔙 список станций",
        "🔙 favoriler menüsü",
        "🔙 favorites menu",
        "🔙 меню избранного",
        "◀️ geri",
        "◀️ back",
        "◀️ назад",
    }

    return (
        (text_lower in generic_back)
        or (text_lower in mapped_back)
        or (text_lower in specific_back)
        or any(k in text_lower for k in ["🔙", "◀️"])
    )


def format_remaining_time(remaining_seconds: float, lang: str) -> str:
    days = int(remaining_seconds // (24 * 3600))
    remaining_seconds %= 24 * 3600
    hours = int(remaining_seconds // 3600)
    remaining_seconds %= 3600
    minutes = int(remaining_seconds // 60)
    seconds = int(remaining_seconds % 60)
    if days > 0:
        return TEXTS["remaining_time_format"][lang].format(days=days, hours=hours, minutes=minutes, seconds=seconds)
    else:
        return TEXTS["remaining_time_format_short"][lang].format(hours=hours, minutes=minutes, seconds=seconds)


async def cleanup_context(context, user_id):
    try:
        import state

        data = await state.get_data(user_id)

        if data.get("message_id"):
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=data["message_id"])
            except Exception as e:
                logger.debug(f"Cleanup single message failed: {e}")

        if "message_ids" in data and isinstance(data["message_ids"], list):
            for mid in data["message_ids"]:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=mid)
                except Exception as e:
                    logger.debug(f"Cleanup batch message failed: {e}")
    except Exception as e:
        logger.debug(f"Cleanup context error: {e}")


async def send_temp_message(update_or_bot, chat_id: int, text: str, delay: float = 5.0):
    try:
        if hasattr(update_or_bot, "message"):
            msg = await update_or_bot.message.reply_text(text)
        else:
            msg = await update_or_bot.send_message(chat_id=chat_id, text=text)

        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except Exception as e:
            logger.debug(f"Temp message delete failed: {e}")
    except Exception as e:
        logger.debug(f"Send temp message error: {e}")


async def delete_user_message(update):
    try:
        if update.message:
            await update.message.delete()
    except Exception as e:
        logger.debug(f"Delete user message failed: {e}")
