import datetime as dt
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class Currency(str, Enum):
    chaos = "chaos"
    divines = "divines"


class ItemPrice(BaseModel):
    """ItemPrice holds information regarding the current, past and future price of an item.
    It stores the recent and predicted prices in a dictionary, with the date as the key."""

    price: Decimal
    currency: Currency
    price_history: dict[dt.datetime, Decimal]
    price_history_currency: Currency
    price_prediction: dict[dt.datetime, Decimal]
    price_prediction_currency: Currency
