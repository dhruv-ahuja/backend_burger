import operator
from typing import Type

from beanie import Document
from beanie.odm.operators.find.evaluation import RegEx as RegExOperator
from loguru import logger
import orjson
import pymongo
from redis.asyncio import Redis, RedisError

from src.config.constants.app import FIND_MANY_QUERY
from src.schemas.requests import FilterInput, SortInput
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


async def delete_cached_data(key: str, redis_client: Redis) -> None:
    """Deletes cached data associated with the given key."""

    try:
        await redis_client.delete(key)
    except RedisError as exc:
        logger.error(f"error deleting cached data: {exc}")
        raise


def sort_on_query(query: FIND_MANY_QUERY, model: Type[Document], sort: SortInput | None) -> FIND_MANY_QUERY:
    """Parses, gathers and chains sort operations on the input query. Skips the process if sort input is empty."""

    if sort is None:
        return query

    sort_expressions = []

    for entry in sort.sort_input:
        field = entry.field
        operation = pymongo.ASCENDING if entry.operation == "asc" else pymongo.DESCENDING

        model_field = getattr(model, field)
        expression = (model_field, operation)

        sort_expressions.append(expression)

    query = query.sort(sort_expressions)
    return query


def filter_on_query(query: FIND_MANY_QUERY, model: Type[Document], filter_: FilterInput | None) -> FIND_MANY_QUERY:
    """Parses, gathers and chains filter operations on the input query. Skips the process if filter input is empty.\n
    Maps the operation list to operator arguments that allow using the operator dynamically, to create expressions
    within the Beanie `find` method."""

    if filter_ is None:
        return query

    operation_map = {
        "=": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "like": RegExOperator,
    }

    for entry in filter_.filter_input:
        field = entry.field
        operation = entry.operation
        operation_function = operation_map[operation]
        value = entry.value

        model_field = getattr(model, field)

        if operation != "like":
            query = query.find(operation_function(model_field, value))
        else:
            operation_function = RegExOperator
            options = "i"  # case-insensitive search

            query = query.find(operation_function(model_field, value, options=options))

    return query
