import datetime as dt
from decimal import Decimal
from enum import Enum

from beanie import Link
from pydantic import Field

from src.models.common import DateMetadataDocument
from src.schemas.poe import Currency


class ItemIdType(str, Enum):
    pay = "pay"
    receive = "receive"


class ItemCategory(DateMetadataDocument):
    """ItemCategory represents a major category that items belong to. A category is the primary form of classifying
    items. Each category belongs to a category group (model not defined for category groups)."""

    name: str
    internal_name: str
    group: str

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_item_categories"


class Item(DateMetadataDocument):
    """Item represents a Path of Exile in-game item. Each item belongs to a category."""

    poe_ninja_id: int
    id_type: ItemIdType | None = None
    name: str
    category: Link[ItemCategory]
    type_: str | None = Field(None, serialization_alias="type")
    variant: str | None = None
    icon_url: str | None = None
    enabled: bool = True

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_items"


class ItemPrice(DateMetadataDocument):
    """ItemPrice holds information regarding the current, past and future price of an item.
    It stores the recent and predicted prices in a dictionary, with the date as the key."""

    item: Link[Item]
    price: Decimal
    currency: Currency
    price_history: dict[dt.datetime, Decimal]
    price_history_currency: Currency
    price_prediction: dict[dt.datetime, Decimal]
    price_prediction_currency: Currency

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_item_prices"
