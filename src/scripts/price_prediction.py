import datetime as dt
from decimal import Decimal
import math
from typing import Annotated

from httpx import AsyncClient, RequestError
from loguru import logger
import pandas as pd
from pydantic import BaseModel, BeforeValidator, Field, TypeAdapter
import pydantic
import statsmodels.api as sm
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression


API_BASE_URL = "https://poe.ninja/api/data"


# schema logic
def convert_price_to_int(value: Decimal):
    return math.ceil(value)


def convert_days_ago_to_date(days_ago: int) -> dt.datetime:
    return dt.datetime.now(dt.UTC) - dt.timedelta(days_ago)


class PriceHistoryEntity(BaseModel):
    count: int
    value: Annotated[int, BeforeValidator(convert_price_to_int)]
    # * convert `daysAgo` int values to date, and export them as `date` when seralizing into dicts or json
    # date_: Annotated[dt.datetime, BeforeValidator(convert_days_ago_to_date)] = Field(alias="daysAgo", serialization_alias="date")
    days_ago: int = Field(alias="daysAgo")


async def get_price_history_data(category_internal_name: str, item_id: int):
    """Gets all available price history data for the given item_id, and parses it into a consistent schema model."""

    logger.debug(f"getting price history data for item_id {item_id} belonging to '{category_internal_name}' category")

    url = f"/itemhistory?league=Necropolis&type={category_internal_name}&itemId={item_id}"

    async with AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.get(url)
            price_history_api_data: list[dict] = response.json()
        except RequestError as exc:
            logger.error(
                f"error getting price history data for item_id {item_id} belonging to '{category_internal_name}' category: {exc}"
            )
            return []

    try:
        ta = TypeAdapter(list[PriceHistoryEntity])
        price_history_data = ta.validate_python(price_history_api_data)
    except pydantic.ValidationError as exc:
        logger.error(
            f"error parsing price history data for item_id {item_id} belonging to '{category_internal_name}' category: {exc}"
        )
        return []

    return price_history_data
