from collections import defaultdict

from loguru import logger

from src.models.poe import Item, ItemCategory
from src.schemas.poe import ItemBase, ItemGroupMapping, ItemCategoryResponse
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


def group_item_categories(item_categories: list[ItemCategoryResponse]) -> list[ItemGroupMapping]:
    """Gathers and groups categories by their parent groups, in a consistent hashmap format."""

    category_group_map = defaultdict(list)
    item_category_groups: list[ItemGroupMapping] = []

    for category in item_categories:
        category_group_map[category.group].append(category)

    for group, members in category_group_map.items():
        group: str
        category_group_map = ItemGroupMapping(group=group, members=members)
        item_category_groups.append(category_group_map)

    return item_category_groups


async def get_items(
    pagination: PaginationInput, filter_sort_input: FilterSortInput | None
) -> tuple[list[ItemBase], int]:
    """Gets items by given category group, and the total items' count in the database."""

    if filter_sort_input is None:
        items_count = await Item.find().count()
        items = await QueryChainer(Item.find(), Item).paginate(pagination).query.find().project(ItemBase).to_list()

        return items, items_count

    items_query = (
        QueryChainer(Item.find(), Item)
        .filter(filter_sort_input.filter_)
        .sort(filter_sort_input.sort)
        .paginate(pagination)
        .query.project(ItemBase)
        .to_list()
    )
    count_query = QueryChainer(Item.find(), Item).filter(filter_sort_input.filter_).query.count()

    try:
        items = await items_query
        items_count = await count_query
    except Exception as exc:
        logger.error(f"error getting items from database; filter_sort: {filter_sort_input}: {exc}")
        raise

    return items, items_count
