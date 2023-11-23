from fastapi import FastAPI
from starlette import status

from .config.services import setup_services
from .config.middleware import LoggingMiddleware
from .schemas.responses import AppResponse, BaseResponse
from .schemas.exceptions import global_exception_handler

app = FastAPI(lifespan=setup_services)
app.add_middleware(LoggingMiddleware)
app.add_exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR, global_exception_handler)


@app.get("/")
async def get():
    """Returns a simple success message indicating that the server is up and running."""

    response = BaseResponse(data={"status": "ok"})
    return AppResponse(response)
