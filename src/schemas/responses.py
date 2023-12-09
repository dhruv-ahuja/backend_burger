from typing import Any, Generic, TypeAlias, TypeVar

import orjson
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, root_validator
from starlette.status import HTTP_200_OK


class BaseError(BaseModel):
    """Defines the base error structure in the application's base response."""

    type: str
    message: str
    fields: list[dict[str, Any]] | None = None


# * defining types here to avoid 'missing declarations' errors
# T represents any Pydantic BaseModel or Beanie Document, dict or list of BaseModel/Document or dict return types
# TODO: define apt type constraints, currently failing with BaseModel constraint
T = TypeVar("T", Any, None)
E = TypeVar("E", BaseError, None)


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


class AppResponse(JSONResponse, Generic[T, E]):
    """Application's core response type, enforces a set structure for the APIs' responses."""

    def __init__(
        self,
        content: BaseResponse[T, E],
        status_code: int = HTTP_200_OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Serialize the given content and pass it to parent class instance, initializing the custom AppResponse class.\n
        setting a `key` wraps the content inside a dictionary, like so: `{key: content}`."""

        data = content.model_dump()
        super().__init__(data, status_code, headers)

    def render(self, content: Any) -> bytes:
        """Render the content as bytes, and return them to the client."""

        return orjson.dumps(content)


ErrorResponse: TypeAlias = AppResponse[None, E]

SingleRecordResponse: TypeAlias = AppResponse[BaseModel, None]

MultiRecordResponse: TypeAlias = AppResponse[list[BaseModel], None]
