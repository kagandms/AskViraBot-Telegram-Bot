import asyncio
from unittest.mock import MagicMock

from telegram import Chat, Message, Update, User
from telegram.ext import ApplicationBuilder, ContextTypes

from core.loader import load_handlers
from main import handle_buttons_logic
from state import WAITING_FOR_NEW_NOTE_INPUT, get_state, set_state


async def test_bot():
    app = ApplicationBuilder().token("FAKE").build()
    load_handlers(app)

    user_id = 999999

    # Simulate DB set state
    await set_state(user_id, WAITING_FOR_NEW_NOTE_INPUT, {"message_id": 1})

    # Verify DB set state
    st = await get_state(user_id)
    print("State from DB:", st)

    # Create fake update
    user = User(id=user_id, first_name="Test", is_bot=False)
    chat = Chat(id=user_id, type="private")
    msg = Message(message_id=2, date=None, chat=chat, user=user, text="Süt al")

    # In v20.x of python-telegram-bot, Message doesn't take 'user' or 'user' is 'from_user'
    msg = Message(message_id=2, date=None, chat=chat, from_user=user, text="Süt al")
    update = Update(update_id=2, message=msg)

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}

    print("Calling handle_buttons_logic")
    try:
        await handle_buttons_logic(update, context)
        print("handle_buttons_logic completed")
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    asyncio.run(test_bot())
