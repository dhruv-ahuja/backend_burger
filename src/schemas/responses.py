from typing import Any, Generic, Self, Type, TypeAlias, TypeVar

import orjson
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from starlette.status import HTTP_200_OK


class BaseError(BaseModel):
    """Defines the base error structure in the application's base response."""

    type: str
    message: str
    fields: list[dict[str, Any]] | None = None


# * defining types here to avoid 'missing declarations' errors
# T represents any Pydantic BaseModel or Beanie Document, dict or list of BaseModel/Document ordict return types
T = TypeVar(
    "T",
    BaseModel,
    list[BaseModel],
    dict[str, Any],
    list[dict[str, Any]],
    None,
)
E = TypeVar("E", BaseError, None)


class BaseResponse(BaseModel, Generic[T, E]):
    """Defines the base response structure for the application."""

    data: T
    error: E | None = None
    key: str | None = Field(default=None, exclude=True)

    # @model_validator(mode="after")
    # def set_data_alias(self) -> Self:
    #     """Wraps `data` field's value in a dictionary with key set to `key` field's value.\n
    #     Example: `key` = 'users', `data`: List[User] => {}"""

    #     if self.key is not None:
    #         return BaseResponse(data={self.key: self.data})  # type: ignore

    #     return self


class AppResponse(JSONResponse, Generic[T, E]):
    """Application's core response type, enforces a set structure for the APIs' responses."""

    def __init__(
        self,
        content: BaseResponse[T, E],
        status_code: int = HTTP_200_OK,
        headers: dict[str, str] | None = None,
        # key: str | None = None,
    ) -> None:
        """Serialize the given content and pass it to parent class instance, initializing the custom AppResponse class.\n
        setting a `key` wraps the content inside a dictionary, like so: `{key: content}`."""

        # serialize response object into dict; wrap the content inside a dictionary if key is set
        data = content.model_dump()
        # if key:
        #     data = {key: content.model_dump()}
        #     print(data)
        # else:
        #     data = content.model_dump()
        #     print(data)

        super().__init__(data, status_code, headers)

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


ErrorResponse: TypeAlias = AppResponse[None, BaseError]

SingleRecordResponse: TypeAlias = AppResponse[BaseModel, None]

MultiRecordResponse: TypeAlias = AppResponse[list[BaseModel], None]
