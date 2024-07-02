from typing import Annotated, Literal
from fastapi import Body, Query
from pydantic import BaseModel, BeforeValidator, Field, computed_field

from src.config.constants.app import ITEMS_PER_PAGE, MAXIMUM_ITEMS_PER_PAGE


class PaginationInput(BaseModel):
    """PaginationInput encapsulates query parameters required for a paginated response."""

    page: int = Query(1, gt=0)
    per_page: int = Query(ITEMS_PER_PAGE, gt=0, lte=MAXIMUM_ITEMS_PER_PAGE)

    @computed_field
    @property
    def offset(self) -> int:
        """Calculates the offset value for use in database queries."""

        return (self.page - 1) * self.per_page
