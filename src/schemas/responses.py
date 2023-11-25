from typing import Any, Type, TypeVar, Generic, TypeAlias

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.status import HTTP_200_OK
import orjson


class BaseError(BaseModel):
    """Defines the base error structure in the application's base response."""

    type: str
    message: str
    fields: list[dict[str, Any]] | None = None


# * defining types here to avoid 'missing declarations' errors
T = TypeVar("T", Type[BaseModel], dict[str, Any], None)
E = TypeVar("E", BaseError, None)


class BaseResponse(BaseModel, Generic[T, E]):
    """Defines the base response structure for the application."""

    data: T
    error: E | None = None


class AppResponse(JSONResponse, Generic[T, E]):
    """Application's core response type, enforces a set structure for the APIs' responses."""

    def __init__(
        self, content: BaseResponse[T, E], status_code: int = HTTP_200_OK, headers: dict[str, str] | None = None
    ) -> None:
        # serialize response object into dict
        data = content.model_dump()

        super().__init__(data, status_code, headers)

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


ErrorResponse: TypeAlias = AppResponse[None, BaseError]
