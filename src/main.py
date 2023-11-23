from typing import Any
from fastapi import FastAPI

from .config.services import setup_services
from .config.middleware import LoggingMiddleware
from .schemas.responses import AppResponse, BaseResponse

app = FastAPI(lifespan=setup_services)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def get() -> AppResponse[dict[str, Any], None]:
    """Returns a simple success message indicating that the server is up and running."""

    response = BaseResponse(data={"status": "ok"})
    return AppResponse(response)
