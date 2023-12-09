from beanie import Document
from pydantic import Field
from pymongo import IndexModel

from src.schemas.user import UserBase


class User(UserBase, Document):
    """User represents a User of the application."""

    password: str = Field(max_length=64)

    class Settings:
        """Defines the settings for the collection."""

        name = "users"
        indexes = [IndexModel([("email")], name="unique_user_email", unique=True)]
