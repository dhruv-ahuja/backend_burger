import hashlib
from typing import cast

import orjson

from src.config.constants import app as consts
from src.schemas.requests import FilterSchema, FilterSortInput, PaginationInput, SortSchema


CACHEABLE_FILTERS = {
    "category": frozenset({"="}),
    "type_": frozenset({"="}),
}
CACHEABLE_SORTS = frozenset({("price_info.chaos_price", "desc")})


def _get_cacheable_query_parts(
    filter_sort_input: FilterSortInput | None,
) -> tuple[list[FilterSchema], list[SortSchema]] | None:
    """Return validated item-query parts when the request is eligible for response caching."""

    if filter_sort_input is None or not filter_sort_input.filter_ or not filter_sort_input.sort:
        return None

    filters = cast(list[FilterSchema], filter_sort_input.filter_)
    sorts = cast(list[SortSchema], filter_sort_input.sort)
    filter_fields = {entry.field for entry in filters}

    # an upstream request may create ambiguity by duplicating filter fields; avoid caching in such cases
    if "category" not in filter_fields or len(filter_fields) != len(filters):
        return None

    if any(
        entry.field not in CACHEABLE_FILTERS or entry.operation not in CACHEABLE_FILTERS[entry.field]
        for entry in filters
    ):
        return None

    if len(sorts) != 1 or (sorts[0].field, sorts[0].operation) not in CACHEABLE_SORTS:
        return None

    return filters, sorts


def build_items_cache_key(
    pagination: PaginationInput,
    filter_sort_input: FilterSortInput | None,
) -> str | None:
    """Build a canonical, versioned cache key, or return ``None`` when the item query should bypass caching."""

    query_parts = _get_cacheable_query_parts(filter_sort_input)
    if query_parts is None:
        return None

    filters, sorts = query_parts
    canonical_query = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "filters": sorted((entry.field, entry.operation, entry.value) for entry in filters),
        "sorts": [(entry.field, entry.operation) for entry in sorts],
    }
    
    serialized_query = orjson.dumps(canonical_query, option=orjson.OPT_SORT_KEYS)
    query_digest = hashlib.sha256(serialized_query).hexdigest()

    return f"{consts.ITEMS_CACHE_NAMESPACE}:{query_digest}"
