import datetime as dt
from enum import Enum
import re

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, SecretStr, validator

from src.config.constants.app import PASSWORD_REGEX


class Role(str, Enum):
    admin = "admin"
    user = "user"


class UserInput(BaseModel):
    """UserInput holds the user's input during the user creation process."""

    name: str = Field(min_length=3, max_length=255)
    email: EmailStr
    password: SecretStr = Field(min_length=8)

    @validator("password")
    def check_password_length(cls, value: SecretStr) -> SecretStr:
        """Checks the entered password's validity."""

        password_meets_requirements = bool(re.match(PASSWORD_REGEX, value.get_secret_value()))

        if not password_meets_requirements:
            raise ValueError()

        return value


class UserUpdateInput(BaseModel):
    """UserUpdateInput holds the user's input during the user details' update process. Does not hold user's password."""

    name: str = Field(min_length=3, max_length=255)
    email: EmailStr


class UserBase(BaseModel):
    """UserBase is the base user model, representing User instances for API responses. Omits the
    password field for security."""

    id: PydanticObjectId | None = None
    name: str = Field(min_length=3, max_length=255)
    email: EmailStr
    role: Role
    created_time: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)
