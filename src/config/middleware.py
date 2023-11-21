import uuid
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from loguru import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs information relating to the current request and adds context to the request, making it uniqely identifiable."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())

        with logger.contextualize(request_id=request_id):
            start_time = time.time()
            response: Response = await call_next(request)
            end_time = start_time - time.time()

            logger.info(
                f"Completed request: {request.method} {request.url} | time: {end_time} | status: {response.status_code}"
            )

        return response
