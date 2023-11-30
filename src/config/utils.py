from typing import Any
import datetime as dt
import os

from fastapi.exceptions import ValidationException
from pydantic import ValidationError
from mypy_boto3_s3.service_resource import Bucket
from loguru import logger


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

    for log_name in os.listdir(logs_directory):
        try:
            date = log_name.split("_")[2].split(".")[0]
            log_date = dt.datetime.strptime(date, datetime_format)
        except (IndexError, ValueError) as ex:
            print(ex)
            continue

        if end_date >= log_date >= start_date:
            log_path = os.path.join(logs_directory, log_name)
            logs_paths.append((log_path, log_name))

    return logs_paths


def upload_logs_to_s3(bucket: Bucket, target_folder: str, logs_paths: list[tuple[str, str]]) -> None:
    """Uploads gathered logs to the S3 bucket."""

    logger.info("uploading logs to s3")

    for log_path, log_name in logs_paths:
        s3_logs_path = f"{target_folder}/{log_name}"
        try:
            bucket.upload_file(log_path, s3_logs_path)
        except Exception as ex:
            logger.error(f"error uploading log '{log_path}' to s3: {ex}")

    logger.info("successfully uploaded logs to s3")
