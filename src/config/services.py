from contextlib import asynccontextmanager
from enum import Enum
import pathlib
import sys
from typing import Any, AsyncGenerator, TextIO, cast

from fastapi import FastAPI
import boto3
import botocore
from mypy_boto3_sqs import SQSServiceResource
from mypy_boto3_sqs.service_resource import Queue
from mypy_boto3_logs.client import CloudWatchLogsClient
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import beanie
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
import boto3.exceptions
import botocore.errorfactory
from watchtower import CloudWatchLogHandler

from .consts import LOG_DIRECTORY, LOGGER_FILENAME_FORMAT, LOGGER_MESSAGE_FORMAT, PROJECT_NAME


class AwsService(str, Enum):
    CloudwatchLogs = "logs"
    SQS = "sqs"

    def __str__(self) -> str:
        return self.value


class Settings(BaseSettings):
    """Parses the configuration settings for the application from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    aws_access_key: SecretStr = Field(alias="AWS_ACCESS_KEY_ID")
    aws_access_secret: SecretStr = Field(alias="AWS_SECRET_ACCESS_KEY")
    aws_region_name: str
    sqs_queue_name: str

    db_url: SecretStr


def initialize_aws_session(key_id: str, key_secret: str, region_name: str) -> boto3.Session:
    """Creates and returns a Session object for connecting to AWS services."""

    try:
        session = boto3.Session(aws_access_key_id=key_id, aws_secret_access_key=key_secret, region_name=region_name)
    except boto3.exceptions.Boto3Error as ex:
        logger.error(f"error connecting to AWS: {ex}")
        raise

    return session


def get_aws_service(service: AwsService, session: boto3.Session) -> SQSServiceResource | CloudWatchLogsClient:
    """Gets and returns the AWS resource object's instance."""

    try:
        match service.value:
            case "sqs":
                client = session.resource(service.value)
                return cast(SQSServiceResource, client)
            case "logs":
                client = session.client(service.value)
                return cast(CloudWatchLogsClient, client)
            case _:
                raise ValueError("Enter a valid aws service.")
    except boto3.exceptions.Boto3Error as ex:
        logger.error(f"error accessing {service} AWS service: {ex}")
        raise


def initialize_logger(
    format: str, path: pathlib.Path | None = None, filename: str | TextIO = sys.stderr, rotation: str | int = "00:00"
) -> None:
    """Initializes the logger with the given configuration parameters.\n
    Uses `rotation` and `path` only when supplying a log file name."""

    configuration = {"format": format, "colorize": True, "enqueue": True}

    if isinstance(filename, str):
        if path is not None:
            file_directory = path.joinpath(filename)
        else:
            file_directory = pathlib.Path(filename)

        configuration["sink"] = file_directory
        configuration["rotation"] = rotation
    else:
        configuration["sink"] = filename

    logger.remove(0)
    logger.add(**configuration)


def initialize_cloudwatch_handler(
    client: SQSServiceResource | CloudWatchLogsClient,
    log_group: str,
    log_stream: str | None = None,
    retention_period: int = 30,
):
    """Initializes and registers the CloudWatch Logs handler with the application logger."""

    # * workaround to narrow the union type
    if not isinstance(client, CloudWatchLogsClient):
        raise ValueError(f"expected client of type {CloudWatchLogsClient}")

    configuration = {"log_group_name": log_group, "log_group_retention_days": retention_period, "boto3_client": client}
    if log_stream is not None:
        configuration["log_stream_name"] = log_stream

    handler = CloudWatchLogHandler(**configuration)
    logger.add(handler)


def generate_settings_config(env_location: str | None = None) -> Settings:
    """Calls the Settings class' instance, which parses and prepares env vars for use throughout the application.\n
    `env_location` overwrites the default env file location to read from."""

    if env_location is not None:
        settings = Settings(_env_file=env_location)  # type: ignore
    else:
        settings = Settings()  # type: ignore

    return settings


def get_sqs_queue(queue_name: str, client: SQSServiceResource | CloudWatchLogsClient) -> Queue:
    """Fetches and returns an existing queue from the SQS resouce."""

    # * workaround to narrow the union type
    if not isinstance(client, SQSServiceResource):
        raise ValueError(f"expected client of type {SQSServiceResource}")

    try:
        queue = client.get_queue_by_name(QueueName=queue_name)
    except botocore.errorfactory.ClientError as ex:
        logger.error(f"error getting SQS queue: {ex}")
        raise

    return queue


async def connect_to_mongodb(db_url: str, document_models: list) -> None:
    """Connects to the MongoDB database given its URL and list of Beanie `Document` modelss to create, after
    establishing connection."""

    logger.info("connecting to database")

    try:
        client = AsyncIOMotorClient(db_url)
        await beanie.init_beanie(database=client.backendBurger, document_models=document_models)
    except Exception as ex:
        logger.error(f"error initializing database connection: {ex}")
        raise

    logger.info("successfully connected to database")


settings = generate_settings_config()

aws_session = initialize_aws_session(
    settings.aws_access_key.get_secret_value(),
    settings.aws_access_secret.get_secret_value(),
    settings.aws_region_name,
)

cloudwatch_client = get_aws_service(AwsService.CloudwatchLogs, aws_session)
initialize_cloudwatch_handler(cloudwatch_client, PROJECT_NAME, PROJECT_NAME)

sqs_client = get_aws_service(AwsService.SQS, aws_session)
queue = get_sqs_queue(PROJECT_NAME, sqs_client)


@asynccontextmanager
async def setup_services(_: FastAPI) -> AsyncGenerator[None, Any]:
    """Sets up connections to required services on app startup."""

    path = pathlib.Path(LOG_DIRECTORY)
    initialize_logger(LOGGER_MESSAGE_FORMAT, path, LOGGER_FILENAME_FORMAT)

    await connect_to_mongodb(settings.db_url.get_secret_value(), [])

    yield
