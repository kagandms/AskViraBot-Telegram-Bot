import asyncio

from telegram.ext import ApplicationBuilder

from core.loader import load_handlers
from core.router import router


async def main():
    app = ApplicationBuilder().token("FAKE").build()
    load_handlers(app)
    print("Registered states:")
    for k, v in router._handlers.items():
        print(f" - {k}: {v.__name__}")


if __name__ == "__main__":
    asyncio.run(main())
