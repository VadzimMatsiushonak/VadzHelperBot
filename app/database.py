import logging
from peewee import SqliteDatabase, Model, AutoField, CharField, TextField, DateTimeField, ForeignKeyField
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


# User Model
class User(BaseModel):
    id = AutoField()
    username = CharField(unique=True)


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
    db.create_tables([User, Todo])
    logging.info("Database initialized")