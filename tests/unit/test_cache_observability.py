from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from redis.asyncio import RedisError

from src.schemas.responses import BaseResponse
from src.utils.routers import get_or_cache_serialized_entity
from src.utils.services import CacheStatus, record_cache_outcome


CACHE_NAMESPACE = "test:entity"


@pytest.mark.parametrize(
    ("status", "expected_level"),
    [
        ("hit", "DEBUG"),
        ("miss", "DEBUG"),
        ("bypass", "DEBUG"),
        ("read_error", "WARNING"),
        ("write_error", "WARNING"),
    ],
)
def test_record_cache_outcome_adds_structured_log_and_span_attributes(status: CacheStatus, expected_level: str):
    bound_logger = Mock()
    span = Mock()
    span.is_recording.return_value = True

    with patch("src.utils.services.logger.bind", return_value=bound_logger) as bind, patch(
        "src.utils.services.get_current_span", return_value=span
    ):
        record_cache_outcome(CACHE_NAMESPACE, status)

    bind.assert_called_once_with(
        cache_system="redis",
        cache_namespace=CACHE_NAMESPACE,
        cache_status=status,
    )
    bound_logger.log.assert_called_once_with(expected_level, "cache outcome")
    assert span.set_attribute.call_args_list == [
        call("cache.system", "redis"),
        call("cache.namespace", CACHE_NAMESPACE),
        call("cache.status", status),
    ]


def test_record_cache_bypass_includes_reason():
    bound_logger = Mock()
    span = Mock()
    span.is_recording.return_value = True

    with patch("src.utils.services.logger.bind", return_value=bound_logger) as bind, patch(
        "src.utils.services.get_current_span", return_value=span
    ):
        record_cache_outcome(CACHE_NAMESPACE, "bypass", reason="query_not_cacheable")

    bind.assert_called_once_with(
        cache_system="redis",
        cache_namespace=CACHE_NAMESPACE,
        cache_status="bypass",
        cache_reason="query_not_cacheable",
    )
    span.set_attribute.assert_any_call("cache.reason", "query_not_cacheable")


@pytest.mark.asyncio
async def test_get_or_cache_records_hit():
    redis_client = AsyncMock()
    redis_client.get.return_value = b"cached"

    with patch("src.utils.routers.record_cache_outcome") as record:
        result = await get_or_cache_serialized_entity(
            "entity:1",
            Mock(),
            None,
            60,
            redis_client,
            cache_namespace=CACHE_NAMESPACE,
        )

    assert result == b"cached"
    record.assert_called_once_with(CACHE_NAMESPACE, "hit")


@pytest.mark.asyncio
async def test_get_or_cache_records_miss_then_write_error():
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    redis_client.set.side_effect = RedisError("cache unavailable")

    with patch("src.utils.routers.record_cache_outcome") as record:
        await get_or_cache_serialized_entity(
            "entity:1",
            AsyncMock(return_value=BaseResponse(data={"id": 1})),
            None,
            60,
            redis_client,
            fail_open=True,
            cache_namespace=CACHE_NAMESPACE,
        )

    assert record.call_args_list == [
        call(CACHE_NAMESPACE, "miss"),
        call(CACHE_NAMESPACE, "write_error"),
    ]
