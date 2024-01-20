from typing import Awaitable

from redis.asyncio import Redis

from src.schemas.responses import BaseResponse
from src.utils.services import cache_data, get_cached_data, serialize_response


async def get_serialized_entity(
    redis_key: str, get_entity_function: Awaitable, response_key: str | None, expire_in: int | None, redis_client: Redis
) -> bytes:
    """Checks whether the serialized details are present in the cache. Awaits the given `get_entity_function` to get and cache this
    data from the database, if the details were not found. `response_key` sets the custom response
    object key for the `BaseResponse` instance."""

    serialized_entity = await get_cached_data(redis_key, redis_client)

    if serialized_entity is None:
        database_entity = await get_entity_function
        serialized_entity = serialize_response(BaseResponse(data=database_entity, key=response_key))

        await cache_data(redis_key, serialized_entity, expire_in, redis_client)

    return serialized_entity
