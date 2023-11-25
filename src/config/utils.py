from typing import Any
from fastapi.exceptions import ValidationException
from pydantic import ValidationError


def parse_validation_error(exc: ValidationError | ValidationException) -> list[dict[str, Any]]:
    # """Parses and extracts required information from FastAPI endpoints' and Pydantic models' `ValidationError`s."""
    """Parses and extracts required information from FastAPI endpoints' `ValidationException`s."""

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
