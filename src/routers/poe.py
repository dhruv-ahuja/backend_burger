from fastapi import APIRouter, Depends, Query

from src import dependencies as deps
from src.schemas.requests import FilterSortInput, PaginationInput
from src.schemas.web_responses import poe as resp
from src.schemas.responses import AppResponse, BaseResponse
from src.services import poe as service
from src.utils.routers import create_pagination_response


dependencies = [Depends(deps.check_access_token)]
router = APIRouter(prefix="/poe", tags=["Path of Exile"], dependencies=dependencies)


@router.get("/categories", responses=resp.GET_CATEGORIES_RESPONSES)
async def get_all_categories():
    """Gets a list of all item categories from the database, mapped by their group names."""

    item_categories = await service.get_item_categories()
    item_category_mapping = service.group_item_categories(item_categories)

    return AppResponse(BaseResponse(data=item_category_mapping, key="category_groups"))


@router.get("/items", responses=resp.GET_ITEMS_RESPONSES)
async def get_items_by_group(
    category_group: str | None = Query(None, min_length=3, max_length=50),
    pagination: PaginationInput = Depends(),  # using Depends allows us to encapsulate Query params within Pydantic models
    filter_: list[str] | None = Query(None, alias="filter"),
    sort: list[str] | None = Query(None),
):
    """Gets a list of all items belonging to the given category group."""

    filter_sort_input = FilterSortInput(sort=sort, filter=filter_)
    items, total_items = await service.get_items(category_group, pagination, filter_sort_input)

    response = create_pagination_response(items, total_items, pagination, "items")
    return AppResponse(response)
