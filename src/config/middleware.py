import uuid
import asyncio

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.config.exceptions import ERROR_RESPONSE
from src.schemas.responses import AppErrorResponse


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Catches errors occuring during the request lifetime and returns a generic 500 error response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response | AppErrorResponse:
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"error when processing request: {exc}")
            return ERROR_RESPONSE

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs information relating to the current request and adds context to the request, making it uniqely identifiable."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        event_loop = asyncio.get_event_loop()

        with logger.contextualize(request_id=request_id):
            start_time = event_loop.time()
            response: Response = await call_next(request)
            execution_time = event_loop.time() - start_time

            logger.info(
                f"Completed request: {request.method} {request.url} | time: {execution_time} | status: {response.status_code}"
            )

        return response
