import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from app.handlers import dp
from app.database import init_db
from app.endpoints import start_aiohttp_app

async def init_bot() -> Bot:
    """Initialize bot with menu commands"""
    # Initialize Bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Set menu commands
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/todo", description="Create a new todo"),
        BotCommand(command="/get_todos", description="Get list of your todos"),
        BotCommand(command="/get_users", description="Get list of users"),
        # BotCommand(command="/post_users", description="Create new user")
    ]
    await bot.set_my_commands(commands)
    return bot

async def main() -> None:
    # Initialize logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Initialize database
    init_db()

    # Initialize Bot with commands
    bot = await init_bot()

    # Start aiohttp health check server
    asyncio.create_task(start_aiohttp_app())

    # Start bot polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())