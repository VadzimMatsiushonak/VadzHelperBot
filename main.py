import asyncio
import logging
import sys
import json
from datetime import datetime
from os import getenv

from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("BOT_TOKEN")

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()

async def health_check(request):
    """Health check endpoint."""
    return web.Response(text="OK", status=200)

async def start_aiohttp_app():
    """Start aiohttp web server for health check."""
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    logging.info("Health check server started on http://0.0.0.0:8000/health")

def log_message_to_json(message: Message):
    # Prepare the data for logging
    log_data = {
        "message_id": message.message_id,
        "date": message.date.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "chat": {
            "chat_id": message.chat.id,
            "chat_type": message.chat.type,
            "username": message.chat.username,
            "first_name": message.chat.first_name,
            "last_name": message.chat.last_name,
        },
        "user": {
            "user_id": message.from_user.id,
            "is_bot": message.from_user.is_bot,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "username": message.from_user.username,
            "language_code": message.from_user.language_code,
        },
        "text": message.text,
    }

    # Convert to JSON
    json_log = json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))
    
    # Log to console (or save to a file)
    logging.info("message log: %s", json_log)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    log_message_to_json(message)
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")



@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        log_message_to_json(message)
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Start aiohttp health check server in the background
    asyncio.create_task(start_aiohttp_app())

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())