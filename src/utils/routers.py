import math
from typing import Any, Awaitable

from loguru import logger
from redis.asyncio import Redis

from src.schemas.requests import PaginationInput
from src.schemas.responses import BaseResponse, PaginationResponse
from src.utils.services import cache_data, get_cached_data, serialize_response


async def get_or_cache_serialized_entity(
    redis_key: str,
    get_entity_function: Awaitable | None,
    response_key: str | None,
    expire_in: int | None,
    redis_client: Redis,
    response: BaseResponse | None = None,
) -> bytes:
    """Checks whether the serialized details are present in the cache. Awaits the given `get_entity_function` to get and cache this
    data from the database, if the details were not found. Uses the `response` value if its available, instead of
    awaiting the function call.

    `response_key` sets the custom response object key for the `BaseResponse` instance."""

    serialized_entity = await get_cached_data(redis_key, redis_client)

    if serialized_entity is not None:
        logger.debug(f"found cached '{redis_key}' data")
        return serialized_entity

    logger.debug(f"'{redis_key}' not in cache, serializing and adding")

    if response is not None:
        serialized_entity = serialize_response(response)
    else:
        assert get_entity_function is not None

        data = await get_entity_function
        if isinstance(data, BaseResponse):
            serialized_entity = serialize_response(data)
        else:
            serialized_entity = serialize_response(BaseResponse(data=data, key=response_key))

    await cache_data(redis_key, serialized_entity, expire_in, redis_client)
    logger.debug(f"cached '{redis_key}' data")

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
