from typing import Type

import beanie

from .app import AppConfig
from .users import User, BlacklistedToken
from .poe import Item, ItemCategory, ItemGroup, ItemPrice


# group and export models for initializing Beanie connection
document_models: list[Type[beanie.Document]] = [
    User,
    BlacklistedToken,
    AppConfig,
    Item,
    ItemCategory,
    ItemGroup,
    ItemPrice,
]
