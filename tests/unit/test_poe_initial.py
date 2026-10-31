from asyncio import Queue
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.models.poe import Item
from src.scripts.poe_initial import (
    API_BASE_URL,
    ApiItemData,
    Category,
    get_item_api_data,
    prepare_api_data,
    save_items,
)


async def fetch_api_data(response: httpx.Response) -> ApiItemData | None:
    transport = httpx.MockTransport(lambda request: response)

    async with httpx.AsyncClient(base_url=API_BASE_URL, transport=transport) as client:
        return await get_item_api_data("Currency", client)


@pytest.mark.asyncio
async def test_get_item_api_data_returns_response_data():
    lines = [{"currencyTypeName": "Divine Orb"}, {"currencyTypeName": "Chaos Orb"}]
    currency_details = [{"id": 1, "icon": "divine.png"}]

    result = await fetch_api_data(httpx.Response(200, json={"lines": lines, "currencyDetails": currency_details}))

    assert result == ApiItemData(item_data=lines, currency_item_metadata=currency_details)


@pytest.mark.asyncio
async def test_get_item_api_data_returns_none_for_http_error():
    result = await fetch_api_data(httpx.Response(404, json={"error": "not found"}))

    assert result is None


@pytest.mark.asyncio
async def test_get_item_api_data_returns_none_for_invalid_json():
    result = await fetch_api_data(httpx.Response(200, content=b"not json"))

    assert result is None


@pytest.mark.asyncio
async def test_get_item_api_data_returns_none_for_invalid_response_shape():
    result = await fetch_api_data(httpx.Response(200, json={"lines": "not a list"}))

    assert result is None


@pytest.mark.asyncio
async def test_get_item_api_data_preserves_valid_empty_response():
    result = await fetch_api_data(httpx.Response(200, json={"lines": []}))

    assert result == ApiItemData(item_data=[], currency_item_metadata=[])


@pytest.mark.asyncio
async def test_prepare_api_data_reports_failed_category_fetch():
    api_item_data_queue = Queue()
    categories = {"Currency": [Category("Currency", "Currency")]}

    with (
        patch("src.scripts.poe_initial.CATEGORY_GROUP_MAP", categories),
        patch("src.scripts.poe_initial.get_category_by_name", new=AsyncMock(return_value=object())),
        patch("src.scripts.poe_initial.get_item_api_data", new=AsyncMock(return_value=None)),
    ):
        result = await prepare_api_data(api_item_data_queue)

    assert result is False
    assert await api_item_data_queue.get() is None


@pytest.mark.asyncio
async def test_save_items_skips_database_write_for_empty_batch():
    collection = AsyncMock()

    with patch.object(Item, "get_motor_collection", return_value=collection) as get_collection:
        result = await save_items([])

    assert result is True
    get_collection.assert_not_called()
    collection.bulk_write.assert_not_awaited()
