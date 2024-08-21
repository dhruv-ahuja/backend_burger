import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Annotated, TypedDict, cast

from bson import Decimal128
from pydantic import BaseModel, BeforeValidator, Field

from src.utils.jobs import convert_decimal


def convert_decimal_values(values: dict[dt.datetime, str | Decimal128 | Decimal]) -> dict[dt.datetime, Decimal]:
    converted_values = {}

    for key, value in values.items():
        converted_value = value.to_decimal() if isinstance(value, Decimal128) else Decimal(value)
        converted_values[key] = Decimal(converted_value)

    return converted_values


def convert_current_price(value: Decimal | Decimal128 | str) -> Decimal:
    return value.to_decimal() if isinstance(value, Decimal128) else Decimal(value)


class Currency(str, Enum):
    chaos = "chaos"
    divines = "divines"


class ItemIdType(str, Enum):
    pay = "pay"
    receive = "receive"


class ItemPrice(BaseModel):
    """ItemPrice holds information regarding the current, past and future price of an item.
    It stores the recent and predicted prices in a dictionary, with the date as the key."""

    chaos_price: Annotated[Decimal, BeforeValidator(convert_current_price)] = Decimal(0)
    divine_price: Annotated[Decimal, BeforeValidator(convert_current_price)] = Decimal(0)
    price_history: Annotated[dict[dt.datetime, Decimal], BeforeValidator(convert_decimal_values)] = {}
    price_history_currency: Currency = Currency.chaos
    price_prediction: Annotated[dict[dt.datetime, Decimal], BeforeValidator(convert_decimal_values)] = {}
    price_prediction_currency: Currency = Currency.chaos
    low_confidence: bool = False
    listings: int = 0

    def serialize(self) -> dict:
        """Serializes the object instance's data, making it compatible with MongoDB. Converts Decimal values into
        Decimal128 values and datetime keys into string keys."""

        price_history = self.price_history
        price_prediction = self.price_prediction

        serialized_data = self.model_dump()

        # convert datetime keys into string variants
        serialized_data["price_history"] = {str(k): v for k, v in price_history.items()}
        serialized_data["price_prediction"] = {str(k): v for k, v in price_prediction.items()}

        # convert decimal types into Decimal128 types and cast the output as dictionary
        serialized_data = convert_decimal(serialized_data)
        serialized_data = cast(dict, serialized_data)

        return serialized_data


class ItemCategoryResponse(BaseModel):
    """ItemCategoryResponse holds the requisite subset of ItemCategory's data for API responses."""

    name: str
    internal_name: str
    group: str = Field(exclude=True)


class ItemBase(BaseModel):
    """ItemBase encapsulates core fields of the Item document."""

    poe_ninja_id: int
    id_type: ItemIdType | None = None
    name: str
    price_info: ItemPrice | None = None
    type_: str | None = Field(None, serialization_alias="type")
    variant: str | None = None
    icon_url: str | None = None
    links: int | None = None
    # enabled: bool = True


class ItemGroupMapping(TypedDict):
    """ItemGroupMapping maps Category instances to the group that they belong to, in a standardized format."""

    group: str
    members: list[ItemCategoryResponse]
