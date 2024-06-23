from enum import Enum

from beanie import Link
from pydantic import Field, Json

from src.models.common import DateMetadataDocument
from src.schemas.poe import ItemPrice


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
    """Item represents a Path of Exile in-game item. Each item belongs to a category. It contains information such as
    item type and the current, past and predicted pricing, encapsulated in the `ItemPrice` schema."""

    poe_ninja_id: int
    id_type: ItemIdType | None = None
    name: str
    category: Link[ItemCategory]
    price: Json[ItemPrice] | None = None
    type_: str | None = Field(None, serialization_alias="type")
    variant: str | None = None
    icon_url: str | None = None
    enabled: bool = True

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_items"
