from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.config.exceptions import handle_validation_exception
from src.config.middleware import ExceptionHandlerMiddleware, LoggingMiddleware
from src.config.services import setup_services
from src.routers import user
from src.schemas.responses import AppResponse, BaseResponse


app = FastAPI(lifespan=setup_services)

app.include_router(user.router)

app.add_exception_handler(RequestValidationError, handle_validation_exception)
app.add_exception_handler(ValidationError, handle_validation_exception)

app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def get():
    """Returns a simple success message indicating that the server is up and running."""

    response = BaseResponse(data={"status": "ok"})
    return AppResponse(response)
