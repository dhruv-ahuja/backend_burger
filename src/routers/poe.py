from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio.client import Redis

from src.config.constants import app as consts
from src.schemas.requests import FilterSortInput, PaginationInput
from src.schemas.web_responses import poe as resp
from src.schemas.responses import AppResponse, BaseResponse
from src.services import poe as service, poe_cache
import src.utils.routers as router_utils
from src.utils.services import record_cache_outcome


router = APIRouter(prefix="/poe", tags=["Path of Exile"])


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
    """Get items using a cached response when the filter, sort and pagination parameters are cacheable."""

    async def get_items_response():
        items, total_items = await service.get_items(pagination, filter_sort_input)
        response = router_utils.create_pagination_response(items, total_items, pagination, "items")

        return response

    redis_client: Redis = request.app.state.redis
    filter_sort_input = FilterSortInput(sort=sort, filter=filter_)
    redis_key = poe_cache.build_items_cache_key(pagination, filter_sort_input)

    if redis_key is None:
        record_cache_outcome(consts.ITEMS_CACHE_NAMESPACE, "bypass", reason="query_not_cacheable")
        response = await get_items_response()
    else:
        response = await router_utils.get_or_cache_serialized_entity(
            redis_key,
            get_items_response,
            None,
            consts.ITEMS_CACHE_DURATION,
            redis_client,
            fail_open=True,
            cache_namespace=consts.ITEMS_CACHE_NAMESPACE,
        )

    return AppResponse(response)
