from unittest.mock import AsyncMock

import orjson
import pytest
from redis.asyncio import RedisError

from src.schemas.responses import BaseResponse
from src.utils.routers import get_or_cache_serialized_entity


@pytest.mark.asyncio
async def test_get_or_cache_does_not_call_factory_on_cache_hit():
    redis_client = AsyncMock()
    redis_client.get.return_value = b'{"data":{"id":1},"error":null}'
    get_entity = AsyncMock()

    result = await get_or_cache_serialized_entity(
        "entity:1",
        get_entity,
        None,
        60,
        redis_client,
    )

    assert result == b'{"data":{"id":1},"error":null}'
    get_entity.assert_not_called()
    redis_client.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_cache_calls_factory_once_and_caches_on_miss():
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    get_entity = AsyncMock(return_value=BaseResponse(data={"id": 1}))

    result = await get_or_cache_serialized_entity(
        "entity:1",
        get_entity,
        None,
        60,
        redis_client,
    )

    assert orjson.loads(result) == {"data": {"id": 1}, "error": None}
    get_entity.assert_awaited_once_with()
    redis_client.set.assert_awaited_once_with("entity:1", result, ex=60)


@pytest.mark.asyncio
async def test_get_or_cache_falls_back_to_factory_when_cache_read_fails():
    redis_client = AsyncMock()
    redis_client.get.side_effect = RedisError("cache unavailable")
    get_entity = AsyncMock(return_value=BaseResponse(data={"id": 1}))

    result = await get_or_cache_serialized_entity(
        "entity:1",
        get_entity,
        None,
        60,
        redis_client,
        fail_open=True,
    )

    assert orjson.loads(result) == {"data": {"id": 1}, "error": None}
    get_entity.assert_awaited_once_with()
    redis_client.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_cache_returns_source_response_when_cache_write_fails():
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    redis_client.set.side_effect = RedisError("cache unavailable")
    get_entity = AsyncMock(return_value=BaseResponse(data={"id": 1}))

    result = await get_or_cache_serialized_entity(
        "entity:1",
        get_entity,
        None,
        60,
        redis_client,
        fail_open=True,
    )

    assert orjson.loads(result) == {"data": {"id": 1}, "error": None}
    get_entity.assert_awaited_once_with()
    redis_client.set.assert_awaited_once_with("entity:1", result, ex=60)


@pytest.mark.asyncio
async def test_get_or_cache_raises_cache_errors_by_default():
    redis_client = AsyncMock()
    redis_client.get.side_effect = RedisError("cache unavailable")
    get_entity = AsyncMock()

    with pytest.raises(RedisError, match="cache unavailable"):
        await get_or_cache_serialized_entity(
            "entity:1",
            get_entity,
            None,
            60,
            redis_client,
        )

    get_entity.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_cache_raises_cache_write_errors_by_default():
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    redis_client.set.side_effect = RedisError("cache unavailable")
    get_entity = AsyncMock(return_value=BaseResponse(data={"id": 1}))

    with pytest.raises(RedisError, match="cache unavailable"):
        await get_or_cache_serialized_entity(
            "entity:1",
            get_entity,
            None,
            60,
            redis_client,
        )

    get_entity.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_get_or_cache_does_not_swallow_factory_errors_in_fail_open_mode():
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    get_entity = AsyncMock(side_effect=ValueError("source failed"))

    with pytest.raises(ValueError, match="source failed"):
        await get_or_cache_serialized_entity(
            "entity:1",
            get_entity,
            None,
            60,
            redis_client,
            fail_open=True,
        )

    redis_client.set.assert_not_awaited()
