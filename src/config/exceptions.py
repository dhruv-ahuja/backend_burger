from typing import cast

from fastapi import HTTPException, Request, Response

from fastapi.exceptions import ValidationException
from fastapi.responses import ORJSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette import status

from src.schemas.responses import BaseError, BaseResponse
from src.config.constants.app import INTERNAL_SCHEMA_MODELS
from src.config.constants.exceptions import ERROR_MAPPING
from src.utils.config import parse_validation_error


async def handle_validation_exception(request: Request, exc: Exception) -> Response:
    """Catches, parses and converts FastAPI endpoints' parameter and Pydantic models' validation exception into a
    standard error response.\n
    Raises an internal 500 error if an invalid internal Pydantic model caused the error."""

    path = request.url.path

    if isinstance(exc, ValidationError):
        if exc.title in INTERNAL_SCHEMA_MODELS:
            errors = exc.errors(include_url=False)
            logger.error(f"error using internal pydantic model {exc.title} at {path}: {errors}")

            response = BaseResponse(
                data=None,
                error=BaseError(type=ERROR_MAPPING[500].type_, message=ERROR_MAPPING[500].message),
            )
            return ORJSONResponse(response, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    exc = cast(ValidationException, exc)
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
    return ORJSONResponse(content=response.model_dump(), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def handle_not_found_exception(request: Request, exc: Exception) -> Response:
    """Structures general 404 error responses into the app's standard response type. Assigns a general message if no
    custom message is given."""

    exc = cast(HTTPException, exc)
    status_code = exc.status_code

    path = request.url.path
    logger.error(f"hit invalid enpoint: {path}")

    error = ERROR_MAPPING[status_code]
    message = exc.detail if exc.detail else error.message

    response = BaseResponse(data=None, error=BaseError(type=error.type_, message=message))
    return ORJSONResponse(content=response.model_dump(), status_code=status_code)


async def handle_method_not_allowed_exception(request: Request, exc: Exception) -> Response:
    """Returns a structured error response for the 405 error type."""

    exc = cast(HTTPException, exc)
    status_code = exc.status_code

    path = request.url.path
    logger.error(f"request at endpoint {path} with invalid method {request.method}")

    error = ERROR_MAPPING[status_code]

    response = BaseResponse(data=None, error=BaseError(type=error.type_, message=error.message))
    return ORJSONResponse(content=response.model_dump(), status_code=status_code)


async def handle_invalid_input_exception(request: Request, exc: Exception) -> Response:
    """Structures 400 error responses into the app's standard response type."""

    exc = cast(HTTPException, exc)
    status_code = exc.status_code

    path = request.url.path
    logger.error(f"request at endpoint {path} with invalid method {request.method}")

    error = ERROR_MAPPING[status_code]
    message = exc.detail if exc.detail else error.message

    response = BaseResponse(data=None, error=BaseError(type=error.type_, message=message))
    return ORJSONResponse(content=response.model_dump(), status_code=status_code)


async def handle_auth_exception(request: Request, exc: Exception) -> Response:
    """Structures 401 and 403 error responses into the app's standard response type."""

    exc = cast(HTTPException, exc)
    status_code = exc.status_code

    path = request.url.path
    logger.error(f"request at endpoint {path} with invalid method {request.method}")

    error = ERROR_MAPPING[status_code]

    response = BaseResponse(data=None, error=BaseError(type=error.type_, message=error.message))
    return ORJSONResponse(response.model_dump(), status_code=status_code, headers=exc.headers)
