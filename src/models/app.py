from beanie import Document


class AppConfig(Document):
    """AppConfig represents a configuration entry of the application."""

    key: str
    value: str

    class Settings:
        """Defines the settings for the collection."""

        name = "app_config"
