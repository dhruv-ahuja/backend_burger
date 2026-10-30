import pytest

from src.schemas.requests import FilterSortInput, PaginationInput
from src.services.poe import check_default_request_input


def is_cacheable(
    *,
    filters: list[str] | None,
    sort: list[str] | None,
    page: int = 1,
    per_page: int = 100,
) -> bool:
    pagination = PaginationInput(page=page, per_page=per_page)
    filter_sort_input = FilterSortInput(filter=filters, sort=sort)

    return check_default_request_input(pagination, filter_sort_input)


def test_category_filter_with_descending_chaos_price_sort_is_cacheable():
    assert is_cacheable(
        filters=["category:=:UniqueWeapon"],
        sort=["-price_info.chaos_price"],
    )


@pytest.mark.parametrize(
    ("filters", "sort"),
    [
        (None, ["-price_info.chaos_price"]),
        (["category:=:UniqueWeapon"], None),
        (None, None),
    ],
)
def test_missing_filter_or_sort_bypasses_cache(filters: list[str] | None, sort: list[str] | None):
    assert not is_cacheable(filters=filters, sort=sort)


@pytest.mark.xfail(strict=True, reason="multi-filter item queries are not cacheable yet")
def test_unique_weapon_type_filter_should_be_cacheable():
    assert is_cacheable(
        filters=["category:=:UniqueWeapon", "type_:=:Wand"],
        sort=["-price_info.chaos_price"],
    )


@pytest.mark.xfail(strict=True, reason="sort-field validation currently uses an incorrect boolean condition")
def test_unexpected_sort_field_should_bypass_cache():
    assert not is_cacheable(
        filters=["category:=:UniqueWeapon"],
        sort=["-name"],
    )


@pytest.mark.xfail(strict=True, reason="sort-direction validation currently uses an incorrect boolean condition")
def test_ascending_chaos_price_sort_should_bypass_cache():
    assert not is_cacheable(
        filters=["category:=:UniqueWeapon"],
        sort=["price_info.chaos_price"],
    )


@pytest.mark.xfail(strict=True, reason="category filter operations are not validated yet")
def test_non_equality_category_filter_should_bypass_cache():
    assert not is_cacheable(
        filters=["category:like:UniqueWeapon"],
        sort=["-price_info.chaos_price"],
    )
