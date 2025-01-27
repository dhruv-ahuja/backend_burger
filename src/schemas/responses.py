from typing import Any, Generic, TypeVar

from fastapi.responses import ORJSONResponse
from starlette import status
from pydantic import BaseModel, Field, root_validator

from src.config.constants.app import MAXIMUM_ITEMS_PER_PAGE


# T represents any Pydantic BaseModel or Beanie Document, dict or list of BaseModel/Document or dict return types
# TODO: define apt type constraints, currently failing with BaseModel constraint
T = TypeVar("T", Any, None)
E = TypeVar("E", "BaseError", None)


class BaseError(BaseModel):
    """Defines the base error structure in the application's base response."""

    type: str
    message: str
    fields: list[dict[str, Any]] | None = None


class BaseResponse(BaseModel, Generic[T, E]):
    """Defines the base response structure for the application."""

    data: T
    error: E | None = None
    key: str | None = Field(default=None, exclude=True)

    @root_validator(skip_on_failure=True)
    def nest_response_data(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Creates a sub-dictionary inside the response `data` dictionary, if a key value is set."""

        key = values.get("key")
        if key is None:
            return values

        data = values.pop("data")
        values["data"] = {key: data}

        return values


class AppResponse(ORJSONResponse, Generic[T, E]):
    """Custom Response class that prevents the parent `ORJSONResponse` class from re-serializing already serialized
    content."""

    def __init__(
        self,
        content: BaseResponse[T, E] | dict | bytes,
        status_code: int = status.HTTP_200_OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Dumps Pydantic models or keeps content as is, passing it to the parent `__init__` function."""

        if isinstance(content, BaseResponse):
            data = content.model_dump(mode="json")
        else:
            data = content

        super().__init__(data, status_code, headers)

    def render(self, content: Any) -> bytes:
        """Conditionally serialize the content as bytes, and returns it to the client."""

        if isinstance(content, bytes):
            return content

        return super().render(content)


class PaginationResponse(BaseModel):
    """PaginationResponse encapsulates pagination values required by the client."""

    page: int = Field(gt=0)
    per_page: int = Field(gt=0, le=MAXIMUM_ITEMS_PER_PAGE)
    total_items: int
    total_pages: int
