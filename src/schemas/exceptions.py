from starlette import status

from src.schemas.responses import AppResponse, BaseError, BaseResponse


ERROR_RESPONSE = AppResponse(
    content=BaseResponse(
        data=None, error=BaseError(type="unknown_error", message="Something went wrong. Please try again later.")
    ),
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
)
