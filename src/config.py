from pydantic import MongoDsn, RedisDsn, SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Manages the configuration settings for the application."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    aws_access_key: SecretStr = Field(alias="AWS_ACCESS_KEY_ID")
    aws_access_secret: SecretStr = Field(alias="AWS_SECRET_ACCESS_KEY")
    aws_region_name: str
    sqs_queue_name: str

    db_url: MongoDsn | None = None
    redis_url: RedisDsn | None = None


settings = Settings()  # type: ignore
