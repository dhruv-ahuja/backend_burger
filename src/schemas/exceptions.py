from fastapi import Request
from fastapi.responses import JSONResponse

from src.schemas.responses import AppResponse, BaseError, BaseResponse


async def global_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Handles global app-level exceptions."""

    error = BaseError(type="unknown_error", message="Something went wrong. Please try again later.")
    data = BaseResponse(data=None, error=error)

    return AppResponse(data)
