import copy
from typing import Self, Type, cast

from beanie import Document
from beanie.odm.operators.find.evaluation import RegEx as RegExOperator
from bson import Decimal128
from loguru import logger
import orjson
import pymongo
from redis.asyncio import Redis, RedisError

from src.config.constants.app import FILTER_OPERATION_MAP, FIND_MANY_QUERY, NESTED_FILTER_OPERATION_MAP
from src.schemas.requests import FilterInputType, FilterSchema, PaginationInput, SortInputType, SortSchema
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


def sort_on_query(query: FIND_MANY_QUERY, model: Type[Document], sort: SortInputType) -> FIND_MANY_QUERY:
    """Parses, gathers and chains sort operations on the input query. Skips the process if sort input is empty."""

    sort = cast(list[SortSchema] | None, sort)
    if not isinstance(sort, list):
        return query

    sort_expressions = []

    for entry in sort:
        field = entry.field
        operation = pymongo.ASCENDING if entry.operation == "asc" else pymongo.DESCENDING

        is_nested = "." in field
        model_field = field if is_nested else getattr(model, field)
        expression = (model_field, operation)

        sort_expressions.append(expression)

    query = query.sort(sort_expressions)
    return query


def _build_nested_query(entry: FilterSchema, query: FIND_MANY_QUERY) -> FIND_MANY_QUERY:
    """Builds queries for nested fields, using raw BSON query syntax to ensure nested fields are parsed properly."""

    field = entry.field
    operation = entry.operation
    value = entry.value

    if operation != "like":
        operation_function = NESTED_FILTER_OPERATION_MAP[operation]
        filter_query = {field: {operation_function: Decimal128(value)}}
    else:
        filter_query = {field: {"$regex": value, "$options": "i"}}

    query = query.find(filter_query)
    return query


def filter_on_query(query: FIND_MANY_QUERY, model: Type[Document], filter_: FilterInputType) -> FIND_MANY_QUERY:
    """Parses, gathers and chains filter operations on the input query. Skips the process if filter input is empty.\n
    Maps the operation list to operator arguments that allow using the operator dynamically, to create expressions
    within the Beanie `find` method."""

    filter_ = cast(list[FilterSchema] | None, filter_)
    if not isinstance(filter_, list):
        return query

    for entry in filter_:
        field = entry.field
        operation = entry.operation
        operation_function = FILTER_OPERATION_MAP[operation]
        value = entry.value

        is_nested = "." in field
        if is_nested:
            query = _build_nested_query(entry, query)
        else:
            model_field = getattr(model, field)

            if operation != "like":
                query = query.find(operation_function(model_field, value))
            else:
                operation_function = RegExOperator
                options = "i"  # case-insensitive search

                query = query.find(operation_function(model_field, value, options=options))

    return query


class QueryChainer:
    def __init__(self, initial_query: FIND_MANY_QUERY, model: Type[Document]) -> None:
        self._query = initial_query
        self.model = model

    def sort(self, sort: SortInputType) -> Self:
        self._query = sort_on_query(self._query, self.model, sort)
        return self

    def filter(self, filter_: FilterInputType) -> Self:
        filter_on_query(self._query, self.model, filter_)
        return self

    def paginate(self, pagination: PaginationInput) -> Self:
        self._query.find(skip=pagination.offset, limit=pagination.per_page)
        return self

    @property
    def query(self) -> FIND_MANY_QUERY:
        return self._query

    def clone(self) -> Self:
        return copy.deepcopy(self)  # type: ignore
