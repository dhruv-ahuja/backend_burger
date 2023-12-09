from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from .config.exceptions import handle_validation_exception
from .config.middleware import ExceptionHandlerMiddleware, LoggingMiddleware
from .config.services import setup_services
from .schemas.responses import AppResponse, BaseResponse

app = FastAPI(lifespan=setup_services)

app.add_exception_handler(RequestValidationError, handle_validation_exception)
app.add_exception_handler(ValidationError, handle_validation_exception)

app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def get():
    """Returns a simple success message indicating that the server is up and running."""

    response = BaseResponse(data={"status": "ok"})
    return AppResponse(response)
