from loguru import logger
import orjson
from redis.asyncio import Redis, RedisError

from src.schemas.responses import E, T, BaseResponse


def serialize_response(response: BaseResponse[T, E] | bytes) -> bytes:
    """Convenience function that serializes responses if they are `BaseResponse`s, else returns them as-is."""

    if isinstance(response, BaseResponse):
        serialized_response = orjson.dumps(response.model_dump())
    else:
        serialized_response = response

    return serialized_response


async def cache_data(key: str, data: bytes, expire_in: int | None, redis_client: Redis) -> None:
    """Caches the given bytes-format data with the given key. Sets the key to expire in the given `expire_in` value.
    The value represents seconds."""

    try:
        await redis_client.set(key, data, ex=expire_in)
    except RedisError as exc:
        logger.error(f"error setting data in cache: {exc}")
        raise


async def get_cached_data(key: str, redis_client: Redis) -> bytes | None:
    """Fetches data associated with the given `key` value. Returns `None` if no data was present."""

    try:
        data = await redis_client.get(key)
    except RedisError as exc:
        logger.error(f"error getting cached data: {exc}")
        raise

    return data


async def delete_cached_data(key: str, redis_client: Redis) -> bytes | None:
    """Fetches data associated with the given `key` value. Returns `None` if no data was present."""

    try:
        data = await redis_client.delete(key)
    except RedisError as exc:
        logger.error(f"error deleting cached data: {exc}")
        raise

    return data
