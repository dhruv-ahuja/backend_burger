from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio.client import Redis

from src import dependencies as deps
from src.config.constants import app as consts
from src.schemas.requests import FilterSortInput, PaginationInput
from src.schemas.web_responses import poe as resp
from src.schemas.responses import AppResponse, BaseResponse
from src.services import poe as service
import src.utils.routers as router_utils


dependencies = [Depends(deps.check_access_token)]
router = APIRouter(prefix="/poe", tags=["Path of Exile"], dependencies=dependencies)


@router.get("/categories", responses=resp.GET_CATEGORIES_RESPONSES)
async def get_all_categories():
    """Gets a list of all item categories from the database, mapped by their group names."""

    item_categories = await service.get_item_categories()
    item_category_mapping = service.group_item_categories(item_categories)

    return AppResponse(BaseResponse(data=item_category_mapping, key="category_groups"))


@router.get("/items", responses=resp.GET_ITEMS_RESPONSES)
async def get_items(
    request: Request,
    pagination: PaginationInput = Depends(),  # using Depends allows us to encapsulate Query params within Pydantic models
    filter_: list[str] | None = Query(None, alias="filter"),
    sort: list[str] | None = Query(None),
):
    """Gets a list of all items, filtered and modified by any given request parameters. Uses cached or caches result
    dataset if using default parameters."""

    async def get_items_response():
        items, total_items = await service.get_items(pagination, filter_sort_input)
        response = router_utils.create_pagination_response(items, total_items, pagination, "items")

        return response

    redis_client: Redis = request.app.state.redis
    redis_key = f"{consts.ITEMS_CACHE_KEY}"

    filter_sort_input = FilterSortInput(sort=sort, filter=filter_)
    is_default_request_input = service.check_default_request_input(pagination, filter_sort_input)

    if not is_default_request_input:
        response = await get_items_response()
    else:
        filter_key = filter_sort_input.filter_[0].value  # type: ignore
        page = pagination.page

        # * get available cached data or cache the data and prepare api resposne
        redis_key = f"{redis_key}:f_{filter_key}:p_{page}"
        response = await router_utils.get_or_cache_serialized_entity(
            redis_key, get_items_response(), None, consts.ITEMS_CACHE_DURATION, redis_client
        )

    return AppResponse(response)
