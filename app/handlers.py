import logging
import json
from aiogram import Dispatcher, F, html
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from app.database import User

# Create the Dispatcher
dp = Dispatcher()

def log_message_to_json(message: Message):
    """Logs a message as JSON.
    
    Args:
        message (Message): The message object to be logged
        
    Returns:
        None
    """
    # Create dictionary with message details
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

    # Convert to JSON and log
    json_log = json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))
    logging.info("message log: %s", json_log)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Handles the `/start` command.
    
    Args:
        message (Message): The message containing the start command
        
    Returns:
        None
    """
    logging.info("Received /start command from user %s", message.from_user.id)
    log_message_to_json(message)
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")
    logging.info("Sent welcome message to user %s", message.from_user.id)


@dp.message(F.text, Command("get_users"))
async def get_users(message: Message):
    """Handles the `/get_users` command to retrieve all users.
    
    Args:
        message (Message): The message containing the get_users command
        
    Returns:
        None
    """
    logging.info("Received /get_users command from user %s", message.from_user.id)
    users = User.select()
    users_list = [{"id": user.id, "username": user.username} for user in users]
    await message.answer(f"Users: {json.dumps(users_list, indent=2)}")
    logging.info("Sent users list to user %s. Total users: %d", message.from_user.id, len(users_list))


@dp.message(F.text, Command("post_users"))
async def post_users(message: Message, command: CommandObject) -> None:
    """Handles the `/post_users` command to create a new user.
    
    Args:
        message (Message): The message containing the post_users command
        command (CommandObject): Command object containing arguments
        
    Returns:
        None
    """
    logging.info("Received /post_users command from user %s", message.from_user.id)
    
    if command.args is None:
        logging.warning("No username provided for /post_users command from user %s", message.from_user.id)
        await message.answer("Please provide a username.\nUsage: /post_users username")
        return
 
    username = command.args
    # Create and save new user
    user = User(username=username)
    user.save()
    logging.info("Created new user with username: %s", username)
    
    await message.answer(f"User {user.username} successfully posted!")
    logging.info("Sent success message for new user creation to user %s", message.from_user.id)



@dp.message()
async def handle_other_messages(message: Message) -> None:
    """Handles any messages that don't match other handlers.
    
    Args:
        message (Message): The unhandled message
        
    Returns:
        None
    """
    logging.info("Received unhandled message from user %s", message.from_user.id)
    await message.answer("Sorry, I don't understand that request. Please use one of the available commands:\n"
                        "/start - Start the bot")
    logging.info("Sent 'invalid request' message to user %s", message.from_user.id)

