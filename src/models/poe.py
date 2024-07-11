from beanie import Link

from src.models.common import DateMetadataDocument
from src.schemas.poe import ItemBase


class ItemCategory(DateMetadataDocument):
    """ItemCategory represents a major category that items belong to. A category is the primary form of classifying
    items. Each category belongs to a category group (model not defined for category groups)."""

    name: str
    internal_name: str
    group: str

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_item_categories"


class Item(ItemBase, DateMetadataDocument):
    """Item represents a Path of Exile in-game item. Each item belongs to a category. It contains information such as
    item type and the current, past and predicted pricing, encapsulated in the `ItemPrice` schema."""

    category: Link[ItemCategory]

    class Settings:
        """Defines the settings for the collection."""

        name = "poe_items"
