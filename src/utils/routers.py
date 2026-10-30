import math
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis, RedisError

from src.schemas.requests import PaginationInput
from src.schemas.responses import BaseResponse, PaginationResponse
from src.utils.services import cache_data, get_cached_data, record_cache_outcome, serialize_response


async def get_or_cache_serialized_entity(
    redis_key: str,
    get_entity_function: Callable[[], Awaitable[Any]] | None,
    response_key: str | None,
    expire_in: int | None,
    redis_client: Redis,
    response: BaseResponse | None = None,
    *,
    fail_open: bool = False,
    cache_namespace: str,
) -> bytes:
    """Checks whether the serialized details are present in the cache. Calls and awaits `get_entity_function` to get
    and cache data from the database only when the details were not found. Uses `response`, when provided, instead of
    calling the entity function.

    `response_key` sets the custom response object key for the `BaseResponse` instance. `cache_namespace` identifies
    this cache in structured logs and traces. When `fail_open` is true, Redis errors bypass the cache without
    preventing the source response from being returned."""

    async def get_serialized_entity() -> bytes:
        if response is not None:
            return serialize_response(response)

        assert get_entity_function is not None

        data = await get_entity_function()
        if isinstance(data, BaseResponse):
            return serialize_response(data)

        return serialize_response(BaseResponse(data=data, key=response_key))

    try:
        serialized_entity = await get_cached_data(redis_key, redis_client)
    except RedisError:
        record_cache_outcome(cache_namespace, "read_error")
        if not fail_open:
            raise

        return await get_serialized_entity()

    if serialized_entity is not None:
        record_cache_outcome(cache_namespace, "hit")
        return serialized_entity

    record_cache_outcome(cache_namespace, "miss")

    serialized_entity = await get_serialized_entity()

    try:
        await cache_data(redis_key, serialized_entity, expire_in, redis_client)
    except RedisError:
        record_cache_outcome(cache_namespace, "write_error")
        if not fail_open:
            raise

    return serialized_entity


def create_pagination_response(data: Any, total_items: int, pagination: PaginationInput, data_key: str) -> BaseResponse:
    """Creates a response structure warpped in a `BaseResponse`, calculating and assigning pagination values."""

    per_page = pagination.per_page
    total_pages = math.ceil(total_items / per_page)

    pagination_response = PaginationResponse(
        page=pagination.page, per_page=pagination.per_page, total_items=total_items, total_pages=total_pages
    )
    response_data = {data_key: data, "pagination": pagination_response}

    response = BaseResponse(data=response_data)
    return response
