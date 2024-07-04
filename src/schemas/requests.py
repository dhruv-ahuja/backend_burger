from typing import Annotated
from fastapi import Body, Query
from pydantic import BaseModel, BeforeValidator, Field, computed_field

from src.config.constants.app import FILTER_OPERATIONS, ITEMS_PER_PAGE, MAXIMUM_ITEMS_PER_PAGE, SORT_OPERATIONS


lowercase_validator = BeforeValidator(lambda v: v.lower())


class PaginationInput(BaseModel):
    """PaginationInput encapsulates query parameters required for a paginated response."""

    page: int = Query(1, gt=0)
    per_page: int = Query(ITEMS_PER_PAGE, gt=0, lte=MAXIMUM_ITEMS_PER_PAGE)

    @computed_field
    @property
    def offset(self) -> int:
        """Calculates the offset value for use in database queries."""

        return (self.page - 1) * self.per_page


class SortInput(BaseModel):
    """SortInput encapsulates the sorting schema model and its implementation as FastAPI's Body object.
    Dependant handler functions will expect a `sort_input` key in the request's JSON body."""

    class SortSchema(BaseModel):
        field: Annotated[str, lowercase_validator]
        operation: Annotated[SORT_OPERATIONS, lowercase_validator]

    sort_input: list[SortSchema] = Field(Body(...))


class FilterInput(BaseModel):
    """FilterInput encapsulates the filter schema model and its implementation as FastAPI's Body object.
    Dependant handler functions will expect a `filter_input` key in the request's JSON body."""

    class FilterSchema(BaseModel):
        field: Annotated[str, lowercase_validator]
        operation: Annotated[FILTER_OPERATIONS, lowercase_validator]
        value: str = Field(min_length=1, max_length=200)

    filter_input: list[FilterSchema] = Field(Body(..., embed=True))
