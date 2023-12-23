import datetime as dt

from beanie import Document, Link

from src.models.users import User


class BlacklistedTokens(Document):
    """BlacklistedTokens contains information regarding tokens blacklisted by the application."""

    user: Link[User]
    token: str
    expiration_time: dt.datetime

    class Settings:
        """Defines the settings for the collection."""

        name = "blacklisted_tokens"
