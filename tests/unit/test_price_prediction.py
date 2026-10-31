from asyncio import Queue
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.models.poe import Item
from src.scripts.price_prediction import API_BASE_URL, ItemRecord, prepare_api_data, update_items_data


async def fetch_price_history(response: httpx.Response):
    item = ItemRecord(id="item-id", name="Test Item", poe_ninja_id=1, category="UniqueWeapon", price_info=None)
    price_history_map = {}
    transport = httpx.MockTransport(lambda request: response)

    async with httpx.AsyncClient(base_url=API_BASE_URL, transport=transport) as client:
        succeeded = await prepare_api_data(item, price_history_map, client)

    return succeeded, price_history_map, item


@pytest.mark.asyncio
async def test_prepare_api_data_reports_http_failure_without_adding_empty_history():
    succeeded, price_history_map, item = await fetch_price_history(
        httpx.Response(404, json={"error": "not found"})
    )

    assert succeeded is False
    assert item not in price_history_map


@pytest.mark.asyncio
async def test_prepare_api_data_preserves_valid_empty_history():
    succeeded, price_history_map, item = await fetch_price_history(httpx.Response(200, json=[]))

    assert succeeded is True
    assert price_history_map[item] == []


@pytest.mark.asyncio
async def test_update_items_data_skips_database_write_for_empty_batch():
    updated_items_queue = Queue()
    await updated_items_queue.put([])
    await updated_items_queue.put(None)
    collection = AsyncMock()

    with patch.object(Item, "get_motor_collection", return_value=collection):
        result = await update_items_data(updated_items_queue)

    assert result is True
    collection.bulk_write.assert_not_awaited()
