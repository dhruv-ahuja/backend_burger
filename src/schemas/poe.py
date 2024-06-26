import datetime as dt
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, Json


class Currency(str, Enum):
    chaos = "chaos"
    divines = "divines"


class ItemIdType(str, Enum):
    pay = "pay"
    receive = "receive"


class ItemPrice(BaseModel):
    """ItemPrice holds information regarding the current, past and future price of an item.
    It stores the recent and predicted prices in a dictionary, with the date as the key."""

    price: Decimal
    currency: Currency
    price_history: dict[dt.datetime, Decimal]
    price_history_currency: Currency
    price_prediction: dict[dt.datetime, Decimal]
    price_prediction_currency: Currency


class ItemCategoryResponse(BaseModel):
    """ItemCategoryResponse holds the requisite subset of ItemCategory's data for API responses."""

    name: str
    internal_name: str
    group: str


class ItemBase(BaseModel):
    """ItemBase encapsulates core fields of the Item document."""

    poe_ninja_id: int
    id_type: ItemIdType | None = None
    name: str
    price: Json[ItemPrice] | None = None
    type_: str | None = Field(None, serialization_alias="type")
    variant: str | None = None
    icon_url: str | None = None
    enabled: bool = True
