from typing import Any

from fastapi.exceptions import ValidationException
from pydantic import ValidationError
import pytest
from pytest import FixtureRequest

from src.config.utils import parse_validation_error


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
