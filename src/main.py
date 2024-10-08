import dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import newrelic.agent
from pydantic import ValidationError
from starlette import status

from src.config.constants.app import CORS_ALLOWED_HOSTS
from src.config.exceptions import (
    handle_validation_exception,
    handle_not_found_exception,
    handle_method_not_allowed_exception,
    handle_invalid_input_exception,
    handle_auth_exception,
)
from src.config.middleware import ExceptionHandlerMiddleware, LoggingMiddleware
from src.config.services import setup_services, initialize_logfire_services, settings
from src.routers import poe, users, auth
from src.schemas.responses import BaseResponse


dotenv.load_dotenv()
newrelic.agent.initialize("./newrelic.ini")


app = FastAPI(
    lifespan=setup_services,
    redirect_slashes=False,
    default_response_class=ORJSONResponse,
    title="Winter Orb",
    version="0.1.0",
    openapi_url=None if settings.app_environment == "prod" else "/openapi.json",
)
initialize_logfire_services(app)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(poe.router)

app.add_exception_handler(status.HTTP_400_BAD_REQUEST, handle_invalid_input_exception)
app.add_exception_handler(RequestValidationError, handle_validation_exception)
app.add_exception_handler(ValidationError, handle_validation_exception)
app.add_exception_handler(status.HTTP_404_NOT_FOUND, handle_not_found_exception)
app.add_exception_handler(status.HTTP_405_METHOD_NOT_ALLOWED, handle_method_not_allowed_exception)
app.add_exception_handler(status.HTTP_401_UNAUTHORIZED, handle_auth_exception)
app.add_exception_handler(status.HTTP_403_FORBIDDEN, handle_auth_exception)

app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get():
    """Returns a simple success message indicating that the server is up and running."""

    return BaseResponse(data={"status": "ok"})
