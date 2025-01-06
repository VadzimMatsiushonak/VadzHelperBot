import logging
import json
from datetime import datetime, timedelta
from aiogram import Dispatcher, F, html
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from app.database import User, ActiveCommand, Todo, TodoStatus

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

    # Create or get existing user
    user, created = User.get_or_create(
        id=message.from_user.id,
        defaults={'username': message.from_user.username or str(message.from_user.id)}
    )

    if created:
        logging.info("Created new user with ID: %d", user.id)
    else:
        logging.info("Found existing user with ID: %d", user.id)

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
        logging.warning("No arguments provided for /post_users command from user %s", message.from_user.id)
        await message.answer("Please provide user ID and username.\nUsage: /post_users id username")
        return

    try:
        user_id, username = command.args.split(maxsplit=1)
        user_id = int(user_id)
    except ValueError:
        logging.warning("Invalid arguments format for /post_users command from user %s", message.from_user.id)
        await message.answer("Invalid format. Please use: /post_users id username")
        return

    # Create and save new user
    user = User(id=user_id, username=username)
    user.save()
    logging.info("Created new user with ID: %d and username: %s", user_id, username)
    
    await message.answer(f"User {user.username} (ID: {user.id}) successfully posted!")
    logging.info("Sent success message for new user creation to user %s", message.from_user.id)

@dp.message(F.text, Command("get_todos"))
async def get_todos(message: Message):
    """Handles the `/get_todos` command to retrieve all todos for a user.
    
    Args:
        message (Message): The message containing the get_todos command
        
    Returns:
        None
    """
    logging.info("Received /get_todos command from user %s", message.from_user.id)
    
    try:
        user = User.get(User.id == message.from_user.id)
        todos = Todo.select().where(Todo.user == user)
        
        todos_list = [{
            "id": todo.id,
            "text": todo.text,
            "status": todo.status,
            "due_date": todo.due_date.strftime("%Y-%m-%d %H:%M:%S")
        } for todo in todos]
        
        await message.answer(f"Your todos:\n{json.dumps(todos_list, indent=2)}")
        logging.info("Sent todos list to user %s. Total todos: %d", message.from_user.id, len(todos_list))
        
    except User.DoesNotExist:
        logging.warning("User %s not found when requesting todos", message.from_user.id)
        await message.answer("You don't have any todos yet. Use /todo to create one!")


@dp.message(F.text, Command("todo"))
async def handle_todo_command(message: Message, command: CommandObject) -> None:
    """Handles the /todo command to create a new todo item.
    
    Args:
        message (Message): The message containing the todo command
        command (CommandObject): Command object containing arguments
        
    Returns:
        None
    """
    logging.info("Received /todo command from user %s", message.from_user.id)
    
    user, _ = User.get_or_create(
        id=message.from_user.id,
        defaults={'username': message.from_user.username}
    )
    
    if command.args is None:
        # Set todo as active command if no args provided
        user.active_command = ActiveCommand.TODO.value
        user.save()
        await message.answer("Please enter your todo text:")
        logging.info("Set todo as active command for user %s", message.from_user.id)
        return
        
    await process_todo(user, command.args, message)
    

async def process_todo(user: User, todo_text: str, message: Message) -> None:
    """Process and create a new todo item.
    
    Args:
        user_id (int): Telegram user ID
        todo_text (str): Text for the todo item
        user (User): User model instance
        message (Message): Message object for sending response
    """
    # Create todo with provided text and due date 1 week from now
    todo = Todo.create(
        text=todo_text,
        status=TodoStatus.PENDING.value,
        user=user,
        due_date=datetime.now() + timedelta(days=7)
    )
    
    # Clear active command if it was set
    if user.active_command:
        user.active_command = None
        user.save()
        
    logging.info("Created new todo for user %s: %s", user.id, todo.text)
    await message.answer(f"Todo created: {todo.text}")


@dp.message()
async def handle_other_messages(message: Message) -> None:
    """Handles any messages that don't match other handlers.
    
    Args:
        message (Message): The unhandled message
        
    Returns:
        None
    """
    logging.info("Received unhandled message from user %s", message.from_user.id)
    
    user = User.get_or_none(id=message.from_user.id)
    if not user:
        await message.answer("Please start the bot first with /start command")
        return
        
    # Handle active commands using match-case
    match user.active_command:
        case ActiveCommand.TODO.value:
            await process_todo(user, message.text, message)
            return
        case _:
            await message.answer("Sorry, I don't understand that request. Please use one of the available commands:\n"
                            "/start - Start the bot\n"
                            "/todo - Create a new todo item")
            logging.info("Sent 'invalid request' message to user %s", message.from_user.id)

