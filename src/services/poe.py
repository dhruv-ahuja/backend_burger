from collections import defaultdict

from fastapi import HTTPException
from loguru import logger
from starlette import status

from src.models.poe import Item, ItemCategory
from src.schemas.poe import ItemBase, ItemCategoryResponse
from src.schemas.requests import FilterSortInput, PaginationInput
from src.utils.services import QueryChainer


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


async def get_items(
    category_group: str | None, pagination: PaginationInput, filter_sort_input: FilterSortInput | None
) -> tuple[list[ItemBase], int]:
    """
    Gets items by given category group, and the total items' count in the database. Raises a 400 error if category
    group is invalid.
    """

    item_category = None
    if category_group is not None:
        try:
            item_category = await ItemCategory.find_one(ItemCategory.group == category_group)
        except Exception as exc:
            logger.error(f"error getting item category by group '{category_group}': {exc} ")
            raise

        if item_category is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid category group.")

    if item_category is None:
        query = Item.find()
    else:
        query = Item.find(Item.category.group == category_group)  # type: ignore

    chainer = QueryChainer(query, Item)

    if filter_sort_input is None:
        items_count = await query.find(fetch_links=True).count()
        items = await chainer.paginate(pagination).query.find(fetch_links=True).project(ItemBase).to_list()

        return items, items_count

    base_query_chain = chainer.filter(filter_sort_input.filter_).sort(filter_sort_input.sort)

    # * clone the query for use with total record counts and pagination calculations
    count_query = (
        base_query_chain.filter(filter_sort_input.filter_)
        .sort(filter_sort_input.sort)
        .clone()
        .query.find(fetch_links=True)
        .count()
    )

    paginated_query = base_query_chain.paginate(pagination).query.find(fetch_links=True).project(ItemBase).to_list()

    try:
        items = await paginated_query
        items_count = await count_query
    except Exception as exc:
        logger.error(
            f"error getting items from database category_group:'{category_group}'; filter_sort: {filter_sort_input}: {exc}"
        )
        raise

    return items, items_count
