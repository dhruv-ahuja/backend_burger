from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
import boto3
from mypy_boto3_sqs import SQSServiceResource
from mypy_boto3_sqs.service_resource import Queue
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import beanie
from motor.motor_asyncio import AsyncIOMotorClient


class Settings(BaseSettings):
    """Parses the configuration settings for the application from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    aws_access_key: SecretStr = Field(alias="AWS_ACCESS_KEY_ID")
    aws_access_secret: SecretStr = Field(alias="AWS_SECRET_ACCESS_KEY")
    aws_region_name: str
    sqs_queue_name: str

    db_url: SecretStr


def generate_settings_config(env_location: str | None = None) -> Settings:
    """Calls the Settings class' instance, which parses and prepares env vars for use throughout the application.\n
    `env_location` overwrites the default env file location to read from."""

    if env_location is not None:
        settings = Settings(_env_file=env_location)  # type: ignore
    else:
        settings = Settings()  # type: ignore

    return settings


def connect_to_sqs(
    key_id: str, key_secret: str, region_name: str
) -> SQSServiceResource:
    """Establishes a connection to the SQS service and returns its resource object."""

    sqs = boto3.resource(
        "sqs",
        aws_access_key_id=key_id,
        aws_secret_access_key=key_secret,
        region_name=region_name,
    )
    return sqs


def get_sqs_queue(sqs: SQSServiceResource, queue_name: str) -> Queue:
    """Fetches and returns a queue from the SQS resouce."""

    queue = sqs.get_queue_by_name(QueueName=queue_name)
    return queue


async def connect_to_mongodb(db_url: str, document_models: list | None = None) -> None:
    """Connects to the MongoDB database given its URL and list of Beanie `Document` modelss to create, after
    establishing connection."""

    print("connecting to Mongo database")

    if document_models is None:
        document_models = []

    client = AsyncIOMotorClient(db_url)
    await beanie.init_beanie(
        database=client.backendBurger, document_models=document_models
    )

    print("successfully connected")


settings = generate_settings_config()

sqs = connect_to_sqs(
    settings.aws_access_key.get_secret_value(),
    settings.aws_access_secret.get_secret_value(),
    settings.aws_region_name,
)
queue = get_sqs_queue(sqs, settings.sqs_queue_name)


@asynccontextmanager
async def setup_services(_: FastAPI) -> AsyncGenerator[None, Any]:
    """Sets up connections to required services on app startup."""

    await connect_to_mongodb(settings.db_url.get_secret_value())
    yield
