from typing import Type

import beanie

from .users import User


# group and export models for initializing Beanie connection
document_models: list[Type[beanie.Document]] = [User]
