from typing import Annotated, TypeAlias
from fastapi import Query
from pydantic import BaseModel, BeforeValidator, Field, computed_field

from src.config.constants.app import FILTER_OPERATION, ITEMS_PER_PAGE, MAXIMUM_ITEMS_PER_PAGE, SORT_OPERATION


FilterInputType: TypeAlias = list["FilterSchema"] | list[str] | None
SortInputType: TypeAlias = list["SortSchema"] | list[str] | None

lowercase_validator = BeforeValidator(lambda v: v.lower())


class PaginationInput(BaseModel):
    """PaginationInput encapsulates query parameters required for a paginated response."""

    page: int = Query(1, gt=0)
    per_page: int = Query(ITEMS_PER_PAGE, gt=0, le=MAXIMUM_ITEMS_PER_PAGE)

    @computed_field
    @property
    def offset(self) -> int:
        """Calculates the offset value for use in database queries."""

        return (self.page - 1) * self.per_page


class FilterSchema(BaseModel):
    """FilterSchema encapsulates the filter schema model, requiring a field, a valid operation and the value to filter on the field by."""

    field: Annotated[str, lowercase_validator]
    operation: Annotated[FILTER_OPERATION, lowercase_validator]
    value: str = Field(min_length=1, max_length=200)

    @staticmethod
    def parse_filter_input(query_params: list[str] | None) -> list["FilterSchema"] | None:
        if query_params is None:
            return

        filter_params = []
        valid_params = True

        for query_param in query_params:
            try:
                field, operation, value = query_param.split(":")
                if operation not in FILTER_OPERATION.__args__:  # type: ignore
                    valid_params = False
                    break

                filter_param = FilterSchema(field=field, operation=operation, value=value)  # type: ignore
            except Exception:
                valid_params = False

            if not valid_params:
                raise ValueError("Invalid input. Incorrect 'filter' query params.")

            filter_params.append(filter_param)

        return filter_params


class SortSchema(BaseModel):
    """SortInput encapsulates the sorting schema model, requiring the field to sort on, and the sort operation type."""

    field: Annotated[str, lowercase_validator]
    operation: Annotated[SORT_OPERATION, lowercase_validator]

    @staticmethod
    def parse_sort_input(query_params: list[str] | None) -> list["SortSchema"] | None:
        if query_params is None:
            return

        sort_params = []
        valid_params = True
        for query_param in query_params:
            try:
                first_char = query_param[0]
                if first_char == "-":
                    operation: SORT_OPERATION = "desc"
                    field = query_param[1:]
                elif first_char.isalpha():
                    operation: SORT_OPERATION = "asc"
                    field = query_param
                else:
                    valid_params = False
                    break
            except Exception:
                valid_params = False

            if not valid_params:
                raise ValueError("Invalid input. Incorrect 'sort' query params.")

            sort_param = SortSchema(field=field, operation=operation)
            sort_params.append(sort_param)

        return sort_params


class FilterSortInput(BaseModel):
    filter_: Annotated[FilterInputType, BeforeValidator(FilterSchema.parse_filter_input)] = Field(None, alias="filter")
    sort: Annotated[SortInputType, BeforeValidator(SortSchema.parse_sort_input)]

    @staticmethod
    def parse_filter_input(query_params: list[str] | None) -> list[FilterSchema] | None:
        if query_params is None:
            return

        filter_params = []
        valid_params = True

        for query_param in query_params:
            try:
                field, operation, value = query_param.split(":")
                if operation not in FILTER_OPERATION.__args__:  # type: ignore
                    valid_params = False
                    break

                filter_param = FilterSchema(field=field, operation=operation, value=value)  # type: ignore
            except Exception:
                valid_params = False

            if not valid_params:
                raise ValueError("Invalid input. Incorrect 'filter' query params.")

            filter_params.append(filter_param)

        return filter_params
