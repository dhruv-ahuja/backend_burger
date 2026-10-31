import httpx
import pytest

from src.scripts.poe_initial import API_BASE_URL, ApiItemData, get_item_api_data


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
