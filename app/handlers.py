import logging
import json
from datetime import datetime, timedelta
from aiogram import Dispatcher, F, html
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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
async def get_todos(message: Message, command: CommandObject):
    """Handles the `/get_todos` command to retrieve all todos for a user.
    
    Args:
        message (Message): The message containing the get_todos command
        command (CommandObject): Command object containing page number argument
        
    Returns:
        None
    """
    logging.info("Received /get_todos command from user %s", message.from_user.id)
    
    # Get page number from command args, default to 1 if not provided
    page = 1
    if command.args:
        try:
            page = int(command.args)
            if page < 1:
                page = 1
        except ValueError:
            page = 1
            
    await show_todos_page(message.from_user.id, page, message=message)


async def show_todos_page(user_id: int, page: int, message=None, callback_query=None):
    """Common method to show todos page either from command or callback.
    
    Args:
        user_id (int): Telegram user ID
        page (int): Page number to show
        message (Message, optional): Message object for command response
        callback_query (CallbackQuery, optional): Callback query for navigation
    """
    items_per_page = 5
    offset = (page - 1) * items_per_page
    
    try:
        user = User.get(User.id == user_id)
        
        # Get total count for pagination
        total_todos = Todo.select().where(Todo.user == user).count()
        
        if total_todos == 0:
            if message:
                await message.answer("You don't have any todos yet. Use /todo to create one!")
            return

        # Calculate pagination
        total_pages = (total_todos + items_per_page - 1) // items_per_page
        if page > total_pages:
            page = total_pages
            offset = (page - 1) * items_per_page
            
        # Get only the todos for current page
        todos = (Todo.select()
                .where(Todo.user == user)
                .order_by(Todo.due_date)
                .limit(items_per_page)
                .offset(offset))

        # Delete old navigation message if this is a callback
        if callback_query:
            await callback_query.message.delete()
            msg = callback_query.message
        else:
            msg = message
            await msg.answer(f"Your todos (Page {page}/{total_pages}):")
        
        # Show todos
        for todo in todos:
            status_emoji = "✅" if todo.status == TodoStatus.DONE.value else "⭕️"
            due_date = todo.due_date.strftime("%Y-%m-%d %H:%M")
            todo_text = f"{status_emoji} {todo.text}\n"
            todo_text += f"Due: {due_date}"
            
            keyboard = None
            if todo.status != TodoStatus.DONE.value:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="✅ Mark as Done",
                        callback_data=f"done_todo_{todo.id}"
                    )
                ]])
            
            await msg.answer(todo_text, reply_markup=keyboard)
        
        # Add separator
        await msg.answer("-------------")
        
        # Add navigation buttons if needed
        navigation_buttons = []
        if page > 1:
            navigation_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Previous",
                    callback_data=f"get_todos {page-1}"
                )
            )
        if page < total_pages:
            navigation_buttons.append(
                InlineKeyboardButton(
                    text="Next ➡️",
                    callback_data=f"get_todos {page+1}"
                )
            )
            
        if navigation_buttons:
            navigation_keyboard = InlineKeyboardMarkup(inline_keyboard=[navigation_buttons])
            await msg.answer("Navigate pages:", reply_markup=navigation_keyboard)
            
        if callback_query:
            await callback_query.answer()
            
        logging.info("Sent todos list page %d to user %s. Showing todos %d-%d of %d", 
                    page, user_id, offset + 1, 
                    min(offset + items_per_page, total_todos), total_todos)
        
    except User.DoesNotExist:
        error_msg = "You don't have any todos yet. Use /todo to create one!"
        if callback_query:
            logging.error("User %s not found for get_todos callback", user_id)
            await callback_query.answer("Error: User not found!", show_alert=True)
        else:
            logging.warning("User %s not found when requesting todos", user_id)
            await message.answer(error_msg)


@dp.callback_query(F.data.startswith("done_todo_"))
async def handle_done_todo_callback(callback_query):
    """Handle callback when user marks a todo as done.
    
    Args:
        callback_query: The callback query from the inline button
        
    Returns:
        None
    """
    try:
        # Extract todo ID from callback data
        todo_id = int(callback_query.data.split("_")[-1])
        
        # Get todo and update status
        todo = Todo.get_by_id(todo_id)
        todo.status = TodoStatus.DONE.value
        todo.save()
        
        # Update message text with done emoji
        due_date = todo.due_date.strftime("%Y-%m-%d %H:%M")
        updated_text = f"✅ {todo.text}\nDue: {due_date}"
        
        # Edit original message to remove keyboard and update text
        await callback_query.message.edit_text(updated_text)
        
        # Answer callback query
        await callback_query.answer("Todo marked as done!")
        
        logging.info("Todo %d marked as done by user %s", 
                    todo_id, callback_query.from_user.id)
                    
    except Todo.DoesNotExist:
        logging.error("Todo %s not found for done callback", todo_id)
        await callback_query.answer("Error: Todo not found!", show_alert=True)
    except Exception as e:
        logging.error("Error handling done todo callback: %s", str(e))
        await callback_query.answer("An error occurred", show_alert=True)


@dp.callback_query(F.data.startswith("get_todos"))
async def handle_get_todos_callback(callback_query):
    """Handle callback for todo list navigation.
    
    Args:
        callback_query: The callback query from the navigation buttons
        
    Returns:
        None
    """
    try:
        # Extract page number from callback data
        page = int(callback_query.data.split()[-1])
        await show_todos_page(callback_query.from_user.id, page, callback_query=callback_query)
                    
    except Exception as e:
        logging.error("Error handling get_todos callback: %s", str(e))
        await callback_query.answer("An error occurred", show_alert=True)


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

