import logging
from peewee import SqliteDatabase, Model, AutoField, CharField, TextField, DateTimeField, ForeignKeyField, IntegerField
from enum import Enum
from config import DB_NAME  # Import database name from config

# Initialize SQLite database
db = SqliteDatabase(DB_NAME)


# Base Model
class BaseModel(Model):
    class Meta:
        database = db


# Enum for Todo Status
class TodoStatus(Enum):
    ACTIVE = "active"
    DONE = "done"
    PENDING = "pending"
    DECLINED = "declined"


# Enum for Active Command
class ActiveCommand(Enum):
    TODO = "todo"


# User Model
class User(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField()
    active_command = CharField(choices=[(cmd.value, cmd.value) for cmd in ActiveCommand], null=True)


# Todo Model
class Todo(BaseModel):
    id = AutoField()
    text = TextField()
    status = CharField(choices=[(status.value, status.value) for status in TodoStatus])
    due_date = DateTimeField()
    user = ForeignKeyField(User, backref="todos")


def init_db():
    """Initialize database and create tables."""
    db.connect()
    db.drop_tables([User, Todo], safe=True)  # Drop existing tables for development environment
    db.create_tables([User, Todo], safe=True) 
    logging.info("Database initialized")