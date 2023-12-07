from typing import Any, Callable
import datetime as dt
import os

from fastapi.exceptions import ValidationException
from pydantic import ValidationError
from mypy_boto3_s3.service_resource import Bucket
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.job import Job

from .constants import logs, app


def parse_validation_error(exc: ValidationError | ValidationException) -> list[dict[str, Any]]:
    """Parses and extracts required information from FastAPI endpoints' and Pydantic models' validation errors."""

    error_data: list[dict[str, Any]] = []
    errors = exc.errors()

    for error in errors:
        error_type: str = error["type"]

        if error_type.endswith("_parsing"):
            expected_type = error_type.split("_parsing")[0]
            error_type = "expected_" + expected_type

        field = error["loc"][-1]

        error_data.append({"error_type": error_type, "field": field})

    return error_data


def gather_logs(logs_directory: str, upload_count: int, datetime_format: str) -> list[tuple[str, str]]:
    """Gather log files from the past N days to upload to S3. `upload_count` represents N."""

    logs_paths = []

    end_date = dt.datetime.today() - dt.timedelta(days=1)
    start_date = end_date - dt.timedelta(days=upload_count)

    logger.info("gathering logs to upload to S3")

    for file_name in os.listdir(logs_directory):
        try:
            date = file_name.split("_")[2].split(".")[0]
            log_date = dt.datetime.strptime(date, datetime_format)
        except (IndexError, ValueError):
            logger.warning(f"log file name '{file_name}' has invalid formatting")
            continue

        if end_date >= log_date >= start_date:
            log_path = os.path.join(logs_directory, file_name)
            logs_paths.append((log_path, file_name))

    logger.info(f"gathered last {upload_count} days' logs successfully")

    return logs_paths


def upload_logs(bucket: Bucket, target_folder: str, logs_paths: list[tuple[str, str]]) -> None:
    """Uploads gathered logs to the S3 bucket."""

    logger.info("uploading logs to s3")

    for log_path, file_name in logs_paths:
        s3_logs_path = f"{target_folder}/{file_name}"
        try:
            bucket.upload_file(log_path, s3_logs_path)
        except Exception as ex:
            logger.error(f"error uploading log '{log_path}' to s3: {ex}")

    logger.info("successfully uploaded logs to s3")


def gather_and_upload_s3_logs(
    bucket: Bucket,
    target_folder: str = app.S3_FOLDER_NAME,
    logs_directory: str = logs.LOGS_DIRECTORY,
    upload_count: int = logs.S3_LOGS_UPLOAD_COUNT,
    datetime_format: str = logs.LOGS_DATETIME_FORMAT,
) -> None:
    """Gathers S3 logs for the given time-period, and uploads them to the S3 bucket's target folder."""

    logs_paths = gather_logs(logs_directory, upload_count, datetime_format)
    upload_logs(bucket, target_folder, logs_paths)


def setup_job(
    scheduler: BackgroundScheduler,
    function: Callable,
    job_id: str | None = None,
    trigger: BaseTrigger | None = None,
    misfire_grace_time: int = 60,
    *args,
    **kwargs,
) -> Job:
    """Creates a background job with the given parameters and registers it with the scheduler."""

    job = scheduler.add_job(function, trigger, args, kwargs, job_id, misfire_grace_tim=misfire_grace_time)

    return job
