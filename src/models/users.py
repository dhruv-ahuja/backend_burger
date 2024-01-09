import datetime as dt
from typing import Annotated

from beanie import Document, Indexed, Link
from pydantic import Field, SecretStr
from pymongo import IndexModel

from src.schemas.users import UserBase


# TODO: add user status and login attempts columns
class User(UserBase, Document):
    """User represents a User of the application."""

    password: SecretStr = Field(min_length=8)

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


class UserSession(Document):
    """UserSession holds information regarding user's latest session."""

    user: Annotated[Link[User], Indexed(unique=True)]
    refresh_token: str
    expiration_time: dt.datetime
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)

    class Settings:
        """Defines the settings for the collection."""

        name = "users_sessions"
