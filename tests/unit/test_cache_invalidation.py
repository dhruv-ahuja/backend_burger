from unittest.mock import AsyncMock, call

import pytest

from src.services.poe_cache import invalidate_items_cache
from src.utils.services import delete_cached_data_matching


@pytest.mark.asyncio
async def test_delete_cached_data_matching_scans_and_unlinks_in_batches():
    redis_client = AsyncMock()
    redis_client.scan.side_effect = [
        (7, [b"poe:items:v2:first", b"poe:items:v2:second"]),
        (0, [b"poe:items:v2:third"]),
    ]
    redis_client.unlink.side_effect = [2, 1]

    deleted_count = await delete_cached_data_matching("poe:items:v2:*", redis_client, scan_count=50)

    assert deleted_count == 3
    assert redis_client.scan.await_args_list == [
        call(cursor=0, match="poe:items:v2:*", count=50),
        call(cursor=7, match="poe:items:v2:*", count=50),
    ]
    assert redis_client.unlink.await_args_list == [
        call(b"poe:items:v2:first", b"poe:items:v2:second"),
        call(b"poe:items:v2:third"),
    ]


@pytest.mark.asyncio
async def test_delete_cached_data_matching_does_not_unlink_an_empty_scan():
    redis_client = AsyncMock()
    redis_client.scan.return_value = (0, [])

    deleted_count = await delete_cached_data_matching("poe:items:v2:*", redis_client)

    assert deleted_count == 0
    redis_client.unlink.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_items_cache_is_limited_to_current_namespace():
    redis_client = AsyncMock()
    redis_client.scan.return_value = (0, [])

    await invalidate_items_cache(redis_client)

    redis_client.scan.assert_awaited_once_with(cursor=0, match="poe:items:v2:*", count=100)
