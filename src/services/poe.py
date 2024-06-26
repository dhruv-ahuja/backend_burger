from collections import defaultdict

from fastapi import HTTPException
from loguru import logger
from starlette import status

from src.models.poe import Item, ItemCategory
from src.schemas.poe import ItemBase, ItemCategoryResponse


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


async def get_items_by_group(category_group: str) -> list[ItemBase]:
    """
    Gets enabled/active items by given category group. Raises a 400 error if category group is invalid.
    """

    try:
        item_category = await ItemCategory.find_one(ItemCategory.group == category_group)
    except Exception as exc:
        logger.error(f"error getting item category by group '{category_group}': {exc} ")
        raise

    if item_category is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid category group.")

    try:
        items = await Item.find(Item.category.group == category_group, fetch_links=True).project(ItemBase).to_list()  # type: ignore

    except Exception as exc:
        logger.error(f"error getting item by category group '{category_group}': {exc}")
        raise

    return items
