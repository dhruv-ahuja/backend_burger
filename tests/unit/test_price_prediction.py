from asyncio import Queue
from unittest.mock import AsyncMock, patch

import pytest

from src.models.poe import Item
from src.scripts.price_prediction import update_items_data


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
