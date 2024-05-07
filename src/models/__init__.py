from typing import Type

import beanie

from .users import User, BlacklistedToken
from .app import AppConfig


# group and export models for initializing Beanie connection
document_models: list[Type[beanie.Document]] = [User, BlacklistedToken, AppConfig]
