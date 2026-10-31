from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.models.poe import Item
from src.scripts.poe_initial import API_BASE_URL, ApiItemData, get_item_api_data, save_items


async def fetch_api_data(response: httpx.Response) -> ApiItemData:
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
async def test_get_item_api_data_returns_empty_data_for_http_error():
    result = await fetch_api_data(httpx.Response(404, json={"error": "not found"}))

    assert result == ApiItemData(item_data=[], currency_item_metadata=[])


@pytest.mark.asyncio
async def test_get_item_api_data_returns_empty_data_for_invalid_json():
    result = await fetch_api_data(httpx.Response(200, content=b"not json"))

    assert result == ApiItemData(item_data=[], currency_item_metadata=[])


@pytest.mark.asyncio
async def test_get_item_api_data_returns_empty_data_for_invalid_response_shape():
    result = await fetch_api_data(httpx.Response(200, json={"lines": "not a list"}))

    assert result == ApiItemData(item_data=[], currency_item_metadata=[])


@pytest.mark.asyncio
async def test_save_items_skips_database_write_for_empty_batch():
    collection = AsyncMock()

    with patch.object(Item, "get_motor_collection", return_value=collection) as get_collection:
        result = await save_items([])

    assert result is True
    get_collection.assert_not_called()
    collection.bulk_write.assert_not_awaited()
