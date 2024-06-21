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


def predict_future_item_prices(data: list[PriceHistoryEntity], days: int = 4):
    df = pd.DataFrame([entity.model_dump() for entity in data])

    # Filter and keep only the last 30 days' data
    df = df.tail(30)
    df["index"] = range(1, len(df) + 1)

    # Set the independent variables (X) and add a constant term
    # NOTE: integrating count (extra variable) would require a more complex model; linear regression takes in 1 value
    X = df[["days_ago"]]
    X = sm.add_constant(X)

    # Set the dependent variable (Y)
    Y = df["value"]

    # Set up PolynomialFeatures and fit_transform X
    poly = PolynomialFeatures(degree=2, include_bias=False)
    X_poly = poly.fit_transform(X.drop(columns=["const"]))  # type: ignore

    # Fit polynomial regression model
    model_poly = LinearRegression()
    model_poly.fit(X_poly, Y)

    # Prepare future data for predictions
    future_days_ago = [df["days_ago"].min() + i for i in range(1, 5)]  # Predicting for next 4 days
    future_count = df["count"].mean()

    future_data = pd.DataFrame({"days_ago": future_days_ago, "count": [future_count] * len(future_days_ago)})
    future_data = pd.DataFrame({"days_ago": future_days_ago})

    future_data_with_const = sm.add_constant(future_data, has_constant="add")  # Add constant term for predictions

    # Transform future data for polynomial regression
    future_X_poly = poly.transform(future_data_with_const.drop(columns=["const"]))  # type: ignore

    # Predict future values using both models
    predictions = model_poly.predict(future_X_poly)

    return predictions
