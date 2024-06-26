from collections import defaultdict
from typing import List

from fastapi import HTTPException
from loguru import logger
from starlette import status

from src.models.poe import Item, ItemCategory
from src.schemas.poe import ItemCategoryResponse


async def get_item_categories() -> list[ItemCategoryResponse]:
    """Gets all item category documents from the database, extracting only the required fields from the documents."""

    try:
        item_categories = await ItemCategory.find_all().project(ItemCategoryResponse).to_list()
    except Exception as exc:
        logger.error(f"error getting item categories: {exc}")
        raise

    return item_categories


def group_item_categories(item_categories: list[ItemCategoryResponse]) -> dict[str, list[ItemCategoryResponse]]:
    """Groups item category documents by their category group."""

    item_category_mapping = defaultdict(list)

    for category in item_categories:
        item_category_mapping[category.group].append(category)

    return item_category_mapping
