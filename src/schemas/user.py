import datetime as dt

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, SecretStr, validator


class UserInput(BaseModel):
    """UserInput holds the user's input during the user creation process."""

    name: str = Field(min_length=3, max_length=255)
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=64)

    @validator("name")
    def check_name_length(cls, input: str) -> str:
        """Checks the entered name's validity."""

        if not 256 > len(input) >= 3:
            raise ValueError("Name length should be between 3 and 256 characters.")

        return input

    # todo: add more stringent password checks
    @validator("password")
    def check_password_length(cls, input: SecretStr) -> SecretStr:
        """Checks the entered password's validity."""

        if not 65 > len(input) >= 8:
            raise ValueError("The password length should be between 8 and 64 characters.")

        return input


class UserBase(BaseModel):
    """UserBase is the base user model, representing User instances for API responses. Omits the
    password field for security."""

    id: PydanticObjectId | None = None
    name: str = Field(min_length=3, max_length=255)
    email: EmailStr
    date_created: dt.datetime = Field(default_factory=dt.datetime.now)
    date_updated: dt.datetime = Field(default_factory=dt.datetime.now)
