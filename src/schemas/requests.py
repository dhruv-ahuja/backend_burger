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


class SortSchema(BaseModel):
    """SortInput encapsulates the sorting schema model, requiring the field to sort on, and the sort operation type."""

    field: Annotated[str, lowercase_validator]
    operation: Annotated[SORT_OPERATIONS, lowercase_validator]


class FilterSchema(BaseModel):
    """FilterSchema encapsulates the filter schema model, requiring a field, a valid operation and the value to filter on the field by."""

    field: Annotated[str, lowercase_validator]
    operation: Annotated[FILTER_OPERATIONS, lowercase_validator]
    value: str = Field(min_length=1, max_length=200)


class FilterSortInput(BaseModel):
    """FilterSortInput wraps filter and sort schema implementations, enabling them to be embedded as JSON body
    parameters for FastAPI request handler functions."""

    filter_: list[FilterSchema] | None = Field(Body(None, embed=True), alias="filter")
    sort: list[SortSchema] | None = Field(Body(None, embed=True))
