import inspect
import os
import sys
import time
import uuid

from fastapi import Request, Response
from fastapi.responses import ORJSONResponse
from loguru import logger
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.config.constants.exceptions import ERROR_MAPPING
from src.schemas.responses import BaseError, BaseResponse


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Catches errors occuring during the request lifetime and returns a generic 500 error response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except Exception as exc:
            exc_type, exc_object, exc_traceback = sys.exc_info()

            # Use inspect to get the correct filename and line number
            frame = inspect.trace()[-1]
            # extract relative filename (/src/...)
            exc_filename = frame[0].f_code.co_filename
            exc_filename = os.path.relpath(exc_filename, start=os.getcwd())
            exc_linenumber = frame[0].f_lineno

            logger.error(
                f"exception type {exc_type}, object: {exc_object} at file {exc_filename}, line no. {exc_linenumber} when processing request: {exc}"
            )

            response = BaseResponse(
                data=None,
                error=BaseError(type=ERROR_MAPPING[500].type_, message=ERROR_MAPPING[500].message),
            )
            return ORJSONResponse(response.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs information relating to the current request and adds context to the request, making it uniqely identifiable."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())

        with logger.contextualize(request_id=request_id):
            start_time = time.monotonic()
            response: Response = await call_next(request)

            execution_time = round(time.monotonic() - start_time, 3)
            execution_time_ms = int(execution_time * 1000)

            response.headers["X-Response-Time"] = str(execution_time_ms)

            logger.info(
                f"Completed request: {request.method} {request.url} | time (ms): {execution_time_ms} | status: {response.status_code}"
            )

        return response
