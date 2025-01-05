import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from app.handlers import dp
from app.database import init_db
from app.endpoints import start_aiohttp_app

async def main() -> None:
    # Initialize logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Initialize database
    init_db()

    # Initialize Bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Start aiohttp health check server
    asyncio.create_task(start_aiohttp_app())

    # Start bot polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())