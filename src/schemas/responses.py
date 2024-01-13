from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, root_validator


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
