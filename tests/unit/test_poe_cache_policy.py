import pytest

from src.schemas.requests import FilterSortInput, PaginationInput
from src.services.poe_cache import build_items_cache_key


def cache_key(
    *,
    filters: list[str] | None,
    sort: list[str] | None,
    page: int = 1,
    per_page: int = 100,
) -> str | None:
    pagination = PaginationInput(page=page, per_page=per_page)
    filter_sort_input = FilterSortInput(filter=filters, sort=sort)

    return build_items_cache_key(pagination, filter_sort_input)


def test_category_filter_with_descending_chaos_price_sort_is_cacheable():
    key = cache_key(
        filters=["category:=:UniqueWeapon"],
        sort=["-price_info.chaos_price"],
    )

    assert key is not None
    assert key.startswith("poe:items:v2:")


@pytest.mark.parametrize(
    ("filters", "sort"),
    [
        (None, ["-price_info.chaos_price"]),
        (["category:=:UniqueWeapon"], None),
        (None, None),
    ],
)
def test_missing_filter_or_sort_bypasses_cache(filters: list[str] | None, sort: list[str] | None):
    assert cache_key(filters=filters, sort=sort) is None


def test_unique_weapon_type_filter_should_be_cacheable():
    assert cache_key(
        filters=["category:=:UniqueWeapon", "type_:=:Wand"],
        sort=["-price_info.chaos_price"],
    )


def test_unexpected_sort_field_should_bypass_cache():
    assert (
        cache_key(
            filters=["category:=:UniqueWeapon"],
            sort=["-name"],
        )
        is None
    )


def test_ascending_chaos_price_sort_should_bypass_cache():
    assert (
        cache_key(
            filters=["category:=:UniqueWeapon"],
            sort=["price_info.chaos_price"],
        )
        is None
    )


def test_non_equality_category_filter_should_bypass_cache():
    assert (
        cache_key(
            filters=["category:like:UniqueWeapon"],
            sort=["-price_info.chaos_price"],
        )
        is None
    )


def test_equivalent_filter_orders_share_a_cache_key():
    category_first = cache_key(
        filters=["category:=:UniqueWeapon", "type_:=:Wand"],
        sort=["-price_info.chaos_price"],
    )
    type_first = cache_key(
        filters=["type_:=:Wand", "category:=:UniqueWeapon"],
        sort=["-price_info.chaos_price"],
    )

    assert category_first == type_first


def test_response_shaping_parameters_have_distinct_cache_keys():
    base_key = cache_key(
        filters=["category:=:UniqueWeapon", "type_:=:Wand"],
        sort=["-price_info.chaos_price"],
    )
    distinct_keys = {
        cache_key(
            filters=["category:=:UniqueWeapon", "type_:=:Wand"],
            sort=["-price_info.chaos_price"],
            page=2,
        ),
        cache_key(
            filters=["category:=:UniqueWeapon", "type_:=:Wand"],
            sort=["-price_info.chaos_price"],
            per_page=50,
        ),
        cache_key(
            filters=["category:=:UniqueWeapon", "type_:=:Axe"],
            sort=["-price_info.chaos_price"],
        ),
        cache_key(
            filters=["category:=:UniqueArmour", "type_:=:Wand"],
            sort=["-price_info.chaos_price"],
        ),
    }

    assert None not in distinct_keys
    assert base_key not in distinct_keys
    assert len(distinct_keys) == 4


def test_duplicate_filter_fields_bypass_cache():
    assert (
        cache_key(
            filters=["category:=:UniqueWeapon", "category:=:UniqueArmour"],
            sort=["-price_info.chaos_price"],
        )
        is None
    )
