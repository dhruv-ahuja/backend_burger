import asyncio
import datetime as dt
from decimal import Decimal
import math
import time
from typing import Annotated

from httpx import AsyncClient, HTTPError
from loguru import logger
import motor
import motor.motor_asyncio
from numpy import ndarray
import numpy
import pandas as pd
from pydantic import BaseModel, BeforeValidator, Field, TypeAdapter
import pydantic
import pymongo
import statsmodels.api as sm
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

from src.config.services import connect_to_mongodb
from src.models import document_models
from src.models.poe import Item, ItemCategory
from src.schemas.poe import Currency, ItemPrice


API_BASE_URL = "https://poe.ninja/api/data"


# schema logic
def convert_price_to_int(value: Decimal):
    return math.ceil(value)


class PriceHistoryEntity(BaseModel):
    count: int
    value: Annotated[int, BeforeValidator(convert_price_to_int)]
    days_ago: int = Field(alias="daysAgo")

    def convert_days_ago_to_date(self):
        now = dt.datetime.now(dt.UTC)
        return now - dt.timedelta(self.days_ago)


# TODO: handle exceptions for db queries
async def get_items() -> list[Item]:
    """Gets all Items from the database."""

    # avoiding links here as each object will fetch its own category record
    return await Item.find_all().to_list()


async def get_and_map_categories() -> dict[str, ItemCategory]:
    """Gets and maps category model instances to their Ids."""

    categories = await ItemCategory.find_all().to_list()
    category_map = {str(category.id): category for category in categories}  # type: ignore

    return category_map


async def update_items_data(items: list[Item]) -> None:
    """Bulk-updates item data in the database."""

    bulk_operations = []
    item_collection: motor.motor_asyncio.AsyncIOMotorCollection = Item.get_motor_collection()

    for item in items:
        item_price_json = item.price.model_dump_json() if item.price else None

        bulk_operations.append(
            pymongo.UpdateOne(
                {"_id": item.id},
                # {"_id": {"$oid": str(item.id)}},
                {
                    "$set": {"price": item_price_json},
                },
            )
        )

    try:
        result = await item_collection.bulk_write(bulk_operations)
        print("result from bulk update query:", result)
    except Exception as exc:
        logger.error(f"error bulk writing: {exc}")
        logger.error(f"{type(exc)}")


async def get_price_history_data(category_internal_name: str, item_id: int) -> list[PriceHistoryEntity]:
    """Gets all available price history data for the given item_id, and parses it into a consistent schema model."""

    # logger.debug(f"getting price history data for item_id {item_id} belonging to '{category_internal_name}' category")

    if category_internal_name in ("Currency", "Fragment"):
        url = f"/currencyhistory?league=Necropolis&type={category_internal_name}&currencyId={item_id}"
    else:
        url = f"/itemhistory?league=Necropolis&type={category_internal_name}&itemId={item_id}"

    async with AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            price_history_api_data: list[dict] | dict[str, list[dict]] = response.json()
        except HTTPError as exc:
            logger.error(
                f"error getting price history data for item_id {item_id} belonging to '{category_internal_name}' category: {exc}"
            )
            return []

    try:
        if isinstance(price_history_api_data, dict):
            price_history_api_data = price_history_api_data.pop("receiveCurrencyGraphData")
        ta = TypeAdapter(list[PriceHistoryEntity])
        price_history_data = ta.validate_python(price_history_api_data)
    except pydantic.ValidationError as exc:
        logger.error(
            f"error parsing price history data for item_id {item_id} belonging to '{category_internal_name}' category: {exc}"
        )
        return []

    return price_history_data


def predict_future_item_prices(price_history_data: list[PriceHistoryEntity], days: int = 4) -> ndarray:
    """Predicts future item prices based on the last 30 days' prices, predicting potential value for the next given
    number of days."""

    if len(price_history_data) < 1:
        return numpy.empty(0)

    df = pd.DataFrame([entity.model_dump() for entity in price_history_data])

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
    future_days_ago = [df["days_ago"].min() + i for i in range(1, days + 1)]
    future_count = df["count"].mean()

    future_data = pd.DataFrame({"days_ago": future_days_ago, "count": [future_count] * len(future_days_ago)})
    future_data = pd.DataFrame({"days_ago": future_days_ago})

    future_data_with_const = sm.add_constant(future_data, has_constant="add")  # Add constant term for predictions

    # Transform future data for polynomial regression
    future_X_poly = poly.transform(future_data_with_const.drop(columns=["const"]))  # type: ignore

    # Predict future values using both models
    predictions = model_poly.predict(future_X_poly)

    # print("\nPredictions for the next 4 days:")
    # for i, pred in enumerate(predictions):
    #     print(f"Day {i + 1}: value: {pred:.2f}")

    return predictions


async def main():
    await connect_to_mongodb(document_models)
    s = time.perf_counter()

    items = await get_items()
    category_map = await get_and_map_categories()

    item_price_history_data = []
    item_price_prediction_data = []

    for item in items:
        item_category_id = str(item.category.ref.id)
        try:
            item_category = category_map[item_category_id]
        except KeyError:
            logger.error(f"item category not found for '{item.name}' item with category id: {item_category_id}")
            continue

        price_history_data = await get_price_history_data(item_category.internal_name, item.poe_ninja_id)
        item_price_history_data.append(price_history_data)

        price_predictions = predict_future_item_prices(price_history_data)
        item_price_prediction_data.append(price_predictions)

        await add_item_price_data(items, price_history_data, item_price_prediction_data)

    await update_items_data(items)

    print(f"time taken for predicting prices for {len(items)} items: {time.perf_counter() - s}")


async def add_item_price_data(
    items: list[Item], price_history_data: list[PriceHistoryEntity], item_price_prediction_data: list[ndarray]
):
    """Converts historical price data into the desired format and adds it and current, future price data to respective Item records."""

    now = dt.datetime.now(dt.UTC)

    for item, price_prediction_data in zip(items, item_price_prediction_data):
        if len(price_history_data) < 1:
            continue

        price_prediction_mapping = {}
        price_history_mapping = {}

        for index, value in enumerate(price_prediction_data):
            rounded_value = round(Decimal(value), 2)
            future_date = now + dt.timedelta(index + 1)

            price_prediction_mapping[future_date] = rounded_value

        last_week_price_data = price_history_data[-7:]
        todays_price_data = price_history_data[-1]

        for entity in last_week_price_data:
            previous_date = entity.convert_days_ago_to_date()
            price_history_mapping[previous_date] = entity.value

        # TODO: parse the value as Decimal, not int through Ceil
        item_price_data = ItemPrice(
            price=todays_price_data.value,  # type: ignore
            currency=Currency.chaos,
            price_history=price_history_mapping,
            price_history_currency=Currency.chaos,
            price_prediction=price_prediction_mapping,
            price_prediction_currency=Currency.chaos,
        )
        item.price = item_price_data


if __name__ == "__main__":
    asyncio.run(main())
