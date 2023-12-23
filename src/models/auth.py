import datetime as dt

from beanie import Document, Link

from src.models.users import User


class BlacklistedToken(Document):
    """BlacklistedToken holds information regarding a token blacklisted by the application."""

    user: Link[User]
    token: str
    expiration_time: dt.datetime

    class Settings:
        """Defines the settings for the collection."""

        name = "blacklisted_tokens"
