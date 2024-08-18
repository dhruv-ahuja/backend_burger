import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Annotated, TypedDict

from bson import Decimal128
from pydantic import BaseModel, BeforeValidator, Field


def convert_decimal_values(values: dict[dt.datetime, str | Decimal128]) -> dict[dt.datetime, Decimal]:
    converted_values = {}

    for key, value in values.items():
        converted_value = Decimal(value) if isinstance(value, str) else value.to_decimal()
        converted_values[key] = Decimal(converted_value)

    return converted_values


def convert_current_price(value: Decimal | Decimal128 | str) -> Decimal:
    return value.to_decimal() if isinstance(value, Decimal128) else Decimal(value)


class Currency(str, Enum):
    chaos = "chaos"
    divines = "divines"


class ItemIdType(str, Enum):
    pay = "pay"
    receive = "receive"


class ItemPrice(BaseModel):
    """ItemPrice holds information regarding the current, past and future price of an item.
    It stores the recent and predicted prices in a dictionary, with the date as the key."""

    price: Annotated[Decimal, BeforeValidator(convert_current_price)]
    currency: Currency
    price_history: Annotated[dict[dt.datetime, Decimal], BeforeValidator(convert_decimal_values)]
    price_history_currency: Currency
    price_prediction: Annotated[dict[dt.datetime, Decimal], BeforeValidator(convert_decimal_values)]
    price_prediction_currency: Currency


class ItemCategoryResponse(BaseModel):
    """ItemCategoryResponse holds the requisite subset of ItemCategory's data for API responses."""

    name: str
    internal_name: str
    group: str = Field(exclude=True)


class ItemBase(BaseModel):
    """ItemBase encapsulates core fields of the Item document."""

    poe_ninja_id: int
    id_type: ItemIdType | None = None
    name: str
    price_info: ItemPrice | None = None
    type_: str | None = Field(None, serialization_alias="type")
    variant: str | None = None
    icon_url: str | None = None
    enabled: bool = True


class ItemGroupMapping(TypedDict):
    """ItemGroupMapping maps Category instances to the group that they belong to, in a standardized format."""

    group: str
    members: list[ItemCategoryResponse]
