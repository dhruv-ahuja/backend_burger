import datetime as dt
from typing import Any

from fastapi.exceptions import ValidationException
from mypy_boto3_s3.service_resource import Bucket
from pydantic import ValidationError
from pyfakefs.fake_filesystem import FakeFilesystem
import pytest
from pytest import FixtureRequest
from pytest_mock import MockerFixture
from pytest_mock.plugin import MockType

from src.config.constants.app import PROJECT_NAME, S3_FOLDER_NAME
from src.config.constants.logs import LOGS_DATETIME_FORMAT
from src.config.utils import gather_logs, parse_validation_error, upload_logs


@pytest.fixture()
def generate_line_errors(request: FixtureRequest) -> list[dict[str, Any]]:
    """Generate line_errors list to be used with `parse_validation_error` test functions."""

    length_error = {
        "type": "string_too_short",
        "loc": ("body", "name"),
        "msg": "String should have at least 3 characters",
        "input": "",
        "ctx": {"min_length": 3},
        "url": "https://errors.pydantic.dev/2.5/v/string_too_short",
    }
    string_type_error = {
        "type": "string_type",
        "loc": ("body", "password"),
        "msg": "Input should be a valid string",
        "input": 2,
        "url": "https://errors.pydantic.dev/2.5/v/string_type",
    }

    return_errors: bool = request.param
    if not return_errors:
        return []
    return [length_error, string_type_error]


@pytest.fixture()
def init_validation_error(
    generate_line_errors: list[dict[str, Any]], request: FixtureRequest
) -> ValidationError | ValidationException:
    """Initializes and returns either a Pydantic `ValidationError` or FastAPI `ValidationException` error instance."""

    return_pydantic_error = request.param
    if not return_pydantic_error:
        return ValidationException(errors=generate_line_errors)
    return ValidationError.from_exception_data(title="test", line_errors=generate_line_errors)  # type: ignore


@pytest.mark.parametrize("generate_line_errors", [True], indirect=True)
@pytest.mark.parametrize("init_validation_error", [True, False], indirect=True)
def test_parse_validation_error_valid_input(
    generate_line_errors: list[dict[str, Any]], init_validation_error: ValidationError | ValidationException
) -> None:
    """Tests the `parse_validation_error` function with some error types passed to either a Pydantic `ValidationError`
    or FastAPI `ValidationException` error instance, to see whether it parses them correctly."""

    expected_value = [
        {"error_type": "string_too_short", "field": "name"},
        {"error_type": "string_type", "field": "password"},
    ]

    assert parse_validation_error(init_validation_error) == expected_value


@pytest.mark.parametrize("generate_line_errors", [False], indirect=True)
@pytest.mark.parametrize("init_validation_error", [True, False], indirect=True)
def test_parse_validation_error_empty_input(
    generate_line_errors: list[dict[str, Any]], init_validation_error: ValidationError | ValidationException
) -> None:
    """Tests the `parse_validation_error` function with some error types passed to either a Pydantic `ValidationError`
    or FastAPI `ValidationException` error instance, to see whether it parses them correctly."""

    assert parse_validation_error(init_validation_error) == []


@pytest.fixture()
def mock_os_listdir(mocker: MockerFixture) -> MockType:
    """Patches the `os.listdir` function, preparing it to be further modified in a test function or fixture."""

    return mocker.patch("os.listdir")


@pytest.fixture()
def mock_s3_bucket(mocker: MockerFixture) -> MockType:
    """Patches the s3 `Bucket` object, preparing it to be further modified in a test function or fixture."""

    return mocker.Mock(spec=Bucket)


@pytest.fixture()
def generate_logs(fs: FakeFilesystem) -> list[tuple[str, str]]:
    """Generates fake logs directory and some fake logs for the past 7 days, to be used to test the logs-based utility
    functions."""

    logs_directory = fs.create_dir("/logs")
    logs_paths = []

    today = dt.datetime.today()

    # generate fake log files for the last 7 days by increasing date difference
    i = 1
    while i <= 7:
        previous_date = today - dt.timedelta(days=i)

        file_name = PROJECT_NAME + "_" + previous_date.strftime(LOGS_DATETIME_FORMAT) + ".log"

        file_path = f"/logs/{file_name}"
        file = fs.create_file(file_name)

        logs_directory.add_entry(file)
        logs_paths.append((file_path, file_name))

        i += 1

    return logs_paths


def test_gather_logs(generate_logs: list[tuple[str, str]], mock_os_listdir: MockType) -> None:
    """Tests the `gather_logs` function by passing it a mocked `os.listdir` function call, and checks whether it
    correctly gathers logs for the past 7 days."""

    logs_paths = generate_logs
    os_logs_files = []

    # prepare log file names to pass as mocked return type
    for _, file_name in logs_paths:
        os_logs_files.append(file_name)

    upload_count = 7
    logs_directory = "/logs"

    mock_os_listdir.return_value = os_logs_files

    returned_logs_paths = gather_logs(logs_directory, upload_count, LOGS_DATETIME_FORMAT)

    assert returned_logs_paths == logs_paths


def mocked_upload_function(source: str, destination: str) -> tuple[str, str]:
    """Mocked upload function to be used instead of the actual S3 bucket's upload function."""

    return source, destination


def test_upload_logs(generate_logs: list[tuple[str, str]], mock_s3_bucket: MockType) -> None:
    """Tests the `upload_logs` function by passing it a mocked S3 bucket, and checks whether it correctly processes the
    passed logs' paths."""

    logs_paths = generate_logs
    mock_s3_bucket.upload_file.side_effect = mocked_upload_function

    upload_logs(mock_s3_bucket, S3_FOLDER_NAME, logs_paths)

    assert mock_s3_bucket.upload_file.call_count == len(logs_paths)

    for log_path, file_name in logs_paths:
        expected_s3_path = f"{S3_FOLDER_NAME}/{file_name}"
        mock_s3_bucket.upload_file.assert_any_call(log_path, expected_s3_path)
