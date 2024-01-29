import datetime as dt

from beanie import Document, Link
from pydantic import Field, SecretStr
from pymongo import IndexModel

from src.schemas.users import UserBase, UserSession


# TODO: add user status and login attempts columns
class User(UserBase, Document):
    """User represents a User of the application."""

    password: SecretStr = Field(min_length=8)
    session: UserSession | None = None

    class Settings:
        """Defines the settings for the collection."""

        name = "users"
        indexes = [IndexModel([("email")], name="unique_user_email", unique=True)]


class BlacklistedToken(Document):
    """BlacklistedToken holds information regarding an access token blacklisted by the application.\n
    `expiration_time` allows removal of old records from the collection, at regular intervals."""

    user: Link[User]
    access_token: str
    expiration_time: dt.datetime

    class Settings:
        """Defines the settings for the collection."""

        name = "blacklisted_tokens"
