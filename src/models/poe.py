import datetime as dt
from decimal import Decimal

from beanie import Document, Link, Replace, SaveChanges, Update, after_event
from pydantic import Field

from src.schemas.poe import Currency


# TODO: see if we can modularize the created-updated time and update-time aspects
class ItemCategory(Document):
    """ItemCategory represents a major category that items belong to. A category is the primary form of classifying
    items. Each category belongs to a category group (model not defined for category groups)."""

    name: str
    internal_name: str
    group: str
    created_time: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)

    @after_event(Replace, SaveChanges, Update)
    def update_time(self):
        self.updated_time = dt.datetime.now()

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_item_categories"


class ItemGroup(Document):
    """ItemGroup represents a group that items fall under. These are more specific than item categories."""

    name: str
    created_time: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)

    @after_event(Replace, SaveChanges, Update)
    def update_time(self):
        self.updated_time = dt.datetime.now()

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_item_groups"


class Item(Document):
    """Item represents a Path of Exile in-game item."""

    poe_ninja_id: str
    name: str
    category: Link[ItemCategory]
    group: Link[ItemGroup]
    enabled: bool = True
    created_time: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)

    @after_event(Replace, SaveChanges, Update)
    def update_time(self):
        self.updated_time = dt.datetime.now()

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_items"


class ItemPrice(Document):
    """ItemPrice holds information regarding the current, past and future price of an item.
    It stores the recent and predicted prices in a dictionary, with the date as the key."""

    item: Link[Item]
    price: Decimal
    currency: Currency
    price_history: dict[dt.datetime, Decimal]
    price_history_currency: Currency
    price_prediction: dict[dt.datetime, Decimal]
    price_prediction_currency: Currency
    created_time: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)

    @after_event(Replace, SaveChanges, Update)
    def update_time(self):
        self.updated_time = dt.datetime.now()

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_item_prices"
