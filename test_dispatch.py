import asyncio

from telegram.ext import ApplicationBuilder

from core.loader import load_handlers
from core.router import router


async def main():
    app = ApplicationBuilder().token("FAKE").build()
    load_handlers(app)

    # Just check if it's in the dict
    print("Is state in handlers?:", "waiting_for_new_note_input" in router._handlers)

    # Manually call dispatch with None to see if it finds it (it will crash if it finds it, which is good)
    try:
        await router.dispatch("waiting_for_new_note_input", None, None)
    except Exception as e:
        print("Dispatch found handler and crashed as expected:", type(e))


if __name__ == "__main__":
    asyncio.run(main())
