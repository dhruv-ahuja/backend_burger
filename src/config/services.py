from contextlib import asynccontextmanager
import datetime as dt
from enum import Enum
import pathlib
import sys
import typing as t

import beanie
import boto3
import boto3.exceptions
import botocore
import botocore.errorfactory
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from boto3.resources.base import ServiceResource
from fastapi import FastAPI
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from mypy_boto3_logs.client import CloudWatchLogsClient
from mypy_boto3_s3 import S3ServiceResource
from mypy_boto3_s3.service_resource import Bucket
from mypy_boto3_sqs import SQSServiceResource
from mypy_boto3_sqs.service_resource import Queue
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis
from watchtower import CloudWatchLogHandler

from src.config.constants import app, logs
from src.models import document_models
from src.utils import jobs


# TODO: break this module into submodules


class AwsService(str, Enum):
    CloudwatchLogs = "logs"
    SQS = "sqs"
    S3 = "s3"

    def __str__(self) -> str:
        return self.value


class Settings(BaseSettings):
    """Parses the configuration settings for the application from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    aws_access_key: SecretStr = Field(alias="AWS_ACCESS_KEY_ID")
    aws_access_secret: SecretStr = Field(alias="AWS_SECRET_ACCESS_KEY")
    aws_region_name: str
    sqs_queue_name: str

    db_url: SecretStr

    jwt_secret_key: SecretStr

    redis_host: str
    redis_password: SecretStr


def generate_settings_config(env_location: str | None = None) -> Settings:
    """Calls the Settings class' instance, which parses and prepares env vars for use throughout the application.\n
    `env_location` overwrites the default env file location to read from."""

    if env_location is not None:
        settings = Settings(_env_file=env_location)  # type: ignore
    else:
        settings = Settings()  # type: ignore

    return settings


def initialize_aws_session(key_id: str, key_secret: str, region_name: str) -> boto3.Session:
    """Creates and returns a Session object for connecting to AWS services."""

    try:
        session = boto3.Session(
            aws_access_key_id=key_id,
            aws_secret_access_key=key_secret,
            region_name=region_name,
        )
    except boto3.exceptions.Boto3Error as exc:
        logger.error(f"error connecting to AWS: {exc}")
        raise

    return session


def get_aws_service(service: AwsService, session: boto3.Session) -> ServiceResource | CloudWatchLogsClient:
    """Gets and returns the AWS resource object's instance."""

    try:
        match service.value:
            case "sqs" | "s3":
                client = session.resource(service.value)
            case "logs":
                client = session.client(service.value)
            case _:
                raise ValueError("Enter a valid aws service.")
    except boto3.exceptions.Boto3Error as exc:
        logger.error(f"error accessing {service} AWS service: {exc}")
        raise

    return client


def initialize_logger(
    format: str,
    path: pathlib.Path | None = None,
    filename: str | t.TextIO = sys.stderr,
    rotation: str | int = "00:00",
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
    client: ServiceResource | CloudWatchLogsClient,
    log_group: str,
    log_stream: str | None = None,
    retention_period: int = 30,
):
    """Initializes and registers the CloudWatch Logs handler with the application logger."""

    # * workaround to narrow the union type
    client = t.cast(CloudWatchLogsClient, client)

    configuration = {
        "log_group_name": log_group,
        "log_group_retention_days": retention_period,
        "boto3_client": client,
    }
    if log_stream is not None:
        configuration["log_stream_name"] = log_stream

    handler = CloudWatchLogHandler(**configuration)
    logger.add(handler)


def get_sqs_queue(client: ServiceResource | CloudWatchLogsClient, queue_name: str) -> Queue:
    """Fetches and returns an existing queue from the SQS resouce."""

    # * workaround to narrow the union type
    client = t.cast(SQSServiceResource, client)

    try:
        queue = client.get_queue_by_name(QueueName=queue_name)
    except botocore.errorfactory.ClientError as exc:
        logger.error(f"error getting SQS queue: {exc}")
        raise

    return queue


def get_s3_bucket(s3: ServiceResource | CloudWatchLogsClient, bucket_name: str) -> Bucket:
    """Fetches and returns an existing queue from the SQS resouce."""

    # * workaround to narrow the union type
    s3 = t.cast(S3ServiceResource, s3)

    try:
        s3_bucket = s3.Bucket(bucket_name)
    except botocore.errorfactory.ClientError as exc:
        logger.error(f"error getting S3 bucket: {exc}")
        raise

    return s3_bucket


def initialize_aws_services(aws_session: boto3.Session) -> t.Tuple[Queue, Bucket]:
    """Connects to all AWS services and returns AWS re-usable instances. Gathers all AWS services' initialization
    function calls in one place."""

    cloudwatch_client = get_aws_service(AwsService.CloudwatchLogs, aws_session)
    initialize_cloudwatch_handler(cloudwatch_client, app.PROJECT_NAME, app.PROJECT_NAME)

    sqs_client = get_aws_service(AwsService.SQS, aws_session)
    queue = get_sqs_queue(sqs_client, app.PROJECT_NAME)

    s3 = get_aws_service(AwsService.S3, aws_session)
    bucket = get_s3_bucket(s3, app.S3_BUCKET_NAME)

    return (queue, bucket)


async def connect_to_mongodb(db_url: str, document_models: list[t.Type[beanie.Document]]) -> None:
    """Connects to the MongoDB database given its URL and list of Beanie `Document` modelss to create, after
    establishing connection."""

    logger.info("connecting to database")

    try:
        await beanie.init_beanie(database=db_client.backendBurger, document_models=document_models)  # type: ignore
    except Exception as exc:
        logger.error(f"error initializing database connection: {exc}")
        raise

    logger.info("successfully connected to database")


def initialize_redis_service(redis_host: str, redis_password: str) -> Redis:
    """Connects to the redis database given its host and password, and establishes an async connection."""

    redis_client = Redis(host=redis_host, password=redis_password, decode_responses=False)
    return redis_client


@asynccontextmanager
async def setup_services(app_: FastAPI) -> t.AsyncGenerator[None, t.Any]:
    """Sets up connections to and initializes required services on FastAPI app startup. These services live throughout
    the app's execution lifespan.\n
    Injects re-usable services into the FastAPI application state, making them available to all route handler
    functions."""

    path = pathlib.Path(logs.LOGS_DIRECTORY)
    initialize_logger(logs.LOGGER_MESSAGE_FORMAT, path, logs.LOGGER_FILENAME_FORMAT)

    aws_session = initialize_aws_session(
        settings.aws_access_key.get_secret_value(),
        settings.aws_access_secret.get_secret_value(),
        settings.aws_region_name,
    )
    queue, s3_bucket = initialize_aws_services(aws_session)

    await connect_to_mongodb(settings.db_url.get_secret_value(), document_models)

    redis_client = initialize_redis_service(settings.redis_host, settings.redis_password.get_secret_value())

    async_scheduler = AsyncIOScheduler()
    scheduler = BackgroundScheduler()
    jobs.schedule_logs_upload_job(s3_bucket, scheduler)

    delete_older_than = dt.datetime.utcnow() - dt.timedelta(days=1)
    jobs.schedule_tokens_deletion(delete_older_than, async_scheduler)

    scheduler.start()
    async_scheduler.start()

    # inject services into global app state
    app_.state.queue = queue
    app_.state.bucket = s3_bucket
    app_.state.redis = redis_client
    app_.state.scheduler = scheduler

    yield

    scheduler.shutdown()
    async_scheduler.shutdown()


settings = generate_settings_config()
# initialize global client object for use across app
db_client = AsyncIOMotorClient(settings.db_url.get_secret_value())
