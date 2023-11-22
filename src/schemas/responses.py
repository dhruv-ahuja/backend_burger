from typing import Any, Type

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.status import HTTP_200_OK
import orjson


class BaseError(BaseModel):
    """Defines the base error structure in the application's base response."""

    type: str
    message: str
    fields: dict[str, list[str]] | None = None


class BaseResponse(BaseModel):
    """Defines the base response structure for the application."""

    data: Type[BaseModel] | dict[str, Any] | None
    error: BaseError | None = None


class AppResponse(JSONResponse):
    """Application's core response type, enforces a set structure for the APIs' responses."""

    def __init__(
        self, content: BaseResponse, status_code: int = HTTP_200_OK, headers: dict[str, str] | None = None
    ) -> None:
        # serialize response object into dict
        data = content.model_dump()

        super().__init__(data, status_code, headers)

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)
