from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette import status

from src.config.exceptions import (
    handle_validation_exception,
    handle_not_found_exception,
    handle_method_not_allowed_exception,
    handle_invalid_input_exception,
)
from src.config.middleware import ExceptionHandlerMiddleware, LoggingMiddleware
from src.config.services import setup_services
from src.routers import users
from src.schemas.responses import AppResponse, BaseResponse


app = FastAPI(lifespan=setup_services)

app.include_router(users.router)

app.add_exception_handler(RequestValidationError, handle_validation_exception)
app.add_exception_handler(ValidationError, handle_validation_exception)
app.add_exception_handler(status.HTTP_404_NOT_FOUND, handle_not_found_exception)
app.add_exception_handler(status.HTTP_405_METHOD_NOT_ALLOWED, handle_method_not_allowed_exception)
app.add_exception_handler(status.HTTP_400_BAD_REQUEST, handle_invalid_input_exception)

app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def get():
    """Returns a simple success message indicating that the server is up and running."""

    response = BaseResponse(data={"status": "ok"})
    return AppResponse(response)
