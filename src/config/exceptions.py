from fastapi import Request
from fastapi.exceptions import ValidationException
from loguru import logger
from pydantic import ValidationError
from starlette import status

from src.schemas.responses import AppResponse, BaseError, BaseResponse, ErrorResponse
from src.config.constants.app import INTERNAL_SCHEMA_MODELS
from src.config.constants.exceptions import ERROR_MAPPING
from src.config.utils import parse_validation_error

ERROR_RESPONSE = AppResponse(
    content=BaseResponse(
        data=None,
        error=BaseError(type=ERROR_MAPPING[500].type_, message=ERROR_MAPPING[500].message),
    ),
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
)


async def handle_validation_exception(request: Request, exc: ValidationError | ValidationException) -> ErrorResponse:
    """Catches, parses and converts FastAPI endpoints' parameter and Pydantic models' validation exception into a
    standard error response.\n
    Raises an internal 500 error if an invalid internal Pydantic model caused the error."""

    path = request.url.path
    if isinstance(exc, ValidationError):
        if exc.title in INTERNAL_SCHEMA_MODELS:
            errors = exc.errors(include_url=False)
            logger.error(f"error using internal pydantic model {exc.title} at {path}: {errors}")

            return ERROR_RESPONSE

    error_data = parse_validation_error(exc)
    logger.error(f"validation error at {path}: {error_data}")

    response = BaseResponse(
        data=None,
        error=BaseError(
            type=ERROR_MAPPING[422].type_,
            message=ERROR_MAPPING[422].message,
            fields=error_data,
        ),
    )
    return AppResponse(content=response, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
