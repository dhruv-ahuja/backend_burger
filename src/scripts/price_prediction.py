import asyncio
from asyncio import Queue
from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
import time
from typing import Annotated, Any

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
from src.models.poe import Item
from src.schemas.poe import Currency, ItemPrice, PriceDatedData

# TODO: handle extreme decimal case scenarios for items like Mirror of Kalandra

API_BASE_URL = "https://poe.ninja/api/data"
BATCH_SIZE = 500
LEAGUE = "Settlers"


# schema logic
@dataclass
class ItemRecord:
    id: Any
    name: str
    poe_ninja_id: int
    category: str
    price_info: ItemPrice | None

    def __hash__(self):
        return hash(self.id)


def round_off_price(value: float):
    return round(Decimal(value), 2)


class PriceHistoryEntity(BaseModel):
    count: int
    value: Annotated[Decimal, BeforeValidator(round_off_price)]
    days_ago: int = Field(alias="daysAgo")

    def convert_days_ago_to_date(self):
        now = dt.datetime.now(dt.UTC)
        return now - dt.timedelta(self.days_ago)


async def get_items(offset: int, limit: int) -> list[ItemRecord]:
    """Gets all Items from the database."""

    try:
        items_ = await Item.find_all(skip=offset, limit=limit).to_list()
    except Exception as exc:
        logger.error(f"error getting items with offset {offset}: {exc}")
        raise

    items = [
        ItemRecord(
            id=item.id,
            name=item.name,
            poe_ninja_id=item.poe_ninja_id,
            category=item.category,
            price_info=item.price_info,
        )
        for item in items_
    ]
    return items


async def push_items_to_queue(total_items: int, batch_size: int, items_queue: Queue[list[ItemRecord] | None]) -> None:
    """Gets and pushes item data to queue. `items_queue` being a bounded queue ensures that this function only
    gets data from the database when necessary."""

    start = time.perf_counter()
    offset = 0

    while offset < total_items:
        items = await get_items(offset, batch_size)
        await items_queue.put(items)

        offset += batch_size
        logger.debug(f"pushed items data from {offset - batch_size} till offset {offset}")

    # push sentinel value
    await items_queue.put(None)

    logger.info(f"time taken to get all items from database: {time.perf_counter() - start}")


async def prepare_api_data(
    item: ItemRecord, price_history_map: dict[Any, list[PriceHistoryEntity]], client: AsyncClient
) -> None:
    """Helper function to get and prepare Price History API data, and add it to the provided hashmap."""

    item_id = item.poe_ninja_id
    category = item.category

    if category in ("Currency", "Fragment"):
        url = f"currencyhistory?league={LEAGUE}&type={category}&currencyId={item_id}"
    else:
        url = f"itemhistory?league={LEAGUE}&type={category}&itemId={item_id}"

    try:
        response = await client.get(url)
        # response.raise_for_status()
        price_history_api_data: list[dict] | dict[str, list[dict]] = response.json()
    except HTTPError as exc:
        logger.error(
            f"error getting price history data for item_id {item_id} belonging to '{category}' category: {exc}"
        )
        price_history_api_data = []

    try:
        if isinstance(price_history_api_data, dict):
            price_history_api_data = price_history_api_data.pop("receiveCurrencyGraphData", [])
        ta = TypeAdapter(list[PriceHistoryEntity])
        price_history_data = ta.validate_python(price_history_api_data)
    except pydantic.ValidationError as exc:
        logger.error(
            f"error parsing price history data for item_id {item_id} belonging to '{category}' category: {exc}"
        )
        price_history_data = []

    price_history_map[item] = price_history_data


async def get_price_history_data(
    items_queue: Queue[list[ItemRecord] | None],
    price_history_queue: Queue[dict[ItemRecord, list[PriceHistoryEntity]] | None],
) -> None:
    """Gets all available price history data for the available items, and parses them into a consistent schema.
    Maps and pushes the data into a queue for futher processing."""

    while True:
        price_history_map = {}
        items = await items_queue.get()
        if items is None:
            # signal end of production
            await price_history_queue.put(None)
            logger.debug("processed all API calls, stopping...")
            return

        start = time.perf_counter()
        offset = 0
        limit = 5
        total_items = len(items)

        async with AsyncClient(base_url=API_BASE_URL) as client:
            async with asyncio.Semaphore(limit):
                while offset < total_items:
                    items_batch = items[offset : offset + limit]

                    # create and await completion of this batch of items
                    tasks = []

                    for item in items_batch:
                        tasks.append(asyncio.create_task(prepare_api_data(item, price_history_map, client)))

                    for task in tasks:
                        await task

                    offset += limit

                    # * sleep to help avoid rate limiting, also ensures client remains available for API calls
                    await asyncio.sleep(0.5)

            await price_history_queue.put(price_history_map)
            logger.info(f"time taken to get price history data for batch: {time.perf_counter() - start}")


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
    return predictions


async def manage_prediction_data(
    price_history_queue: Queue[dict[ItemRecord, list[PriceHistoryEntity]] | None],
    updated_items_queue: Queue[list[ItemRecord] | None],
) -> None:
    """Manages the flow of incoming price history queue data, predicting future prices based on that, and adds that to
    the price prediction queue. Ensures that data is available for consumption down the chain."""

    # push both price history queue and price_prediction items in one go, to make both the data sets available for saving into the db

    while True:
        updated_items = []
        price_history_map = await price_history_queue.get()
        if price_history_map is None:
            # signal end of production
            await updated_items_queue.put(None)
            logger.info("completed predicting prices for all items...")
            return

        start = time.perf_counter()
        for item, price_history_data in price_history_map.items():
            price_prediction_data = predict_future_item_prices(price_history_data)

            prepare_item_price_data(item, price_history_data, price_prediction_data)
            updated_items.append(item)

        await updated_items_queue.put(updated_items)
        logger.debug(f"time taken to predict for current batch: {time.perf_counter() - start}")


async def update_items_data(updated_items_queue: Queue[list[ItemRecord] | None]) -> None:
    """Bulk-updates item data in the database. Serializes item price schema into a JSON object for insertion into
    the database. Creates an order of Pymongo-native `UpdateOne` operations and bulk writes them for efficiency over
    inserting each record one-by-one."""

    item_collection: motor.motor_asyncio.AsyncIOMotorCollection = Item.get_motor_collection()  # type: ignore

    batch_number = 1
    while True:
        bulk_operations = []

        updated_items = await updated_items_queue.get()
        if updated_items is None:
            logger.debug("finished updating all item records in database, exiting...")
            return

        for item in updated_items:
            assert item.price_info is not None
            serialized_data = item.price_info.serialize_price_data()

            bulk_operations.append(
                pymongo.UpdateOne(
                    {"_id": item.id},
                    {
                        "$set": {"price_info": serialized_data, "updated_time": dt.datetime.now(dt.UTC)},
                    },
                )
            )

        try:
            result = await item_collection.bulk_write(bulk_operations)
            logger.info(f"result from batch number {batch_number}'s bulk update: {result}")

            batch_number += 1
        except Exception as exc:
            logger.error(f"error bulk writing: {exc}")
            logger.error(f"{type(exc)}")


def prepare_item_price_data(
    item: ItemRecord, price_history_data: list[PriceHistoryEntity], price_prediction_data: ndarray
) -> None:
    """Converts historical price data into the desired format and adds it and current, future price data to respective Item records."""

    now = dt.datetime.now(dt.UTC)

    price_prediction = []
    price_history = []

    if len(price_history_data) < 1:
        return

    for index, value in enumerate(price_prediction_data):
        rounded_value = round(Decimal(value), 2)
        future_date = now + dt.timedelta(index + 1)

        price_prediction_record = PriceDatedData(timestamp=future_date, price=rounded_value)
        price_prediction.append(price_prediction_record)

    todays_price_data = price_history_data[-1]

    for entity in price_history_data:
        previous_date = entity.convert_days_ago_to_date()
        price_history_record = PriceDatedData(timestamp=previous_date, price=entity.value)
        price_history.append(price_history_record)

        # TODO: check for low confidence
        price_info = item.price_info
        if price_info is None:
            price_info = item.price_info = ItemPrice()
            price_info.chaos_price = todays_price_data.value

        price_info.price_prediction = price_prediction
        price_info.price_prediction_currency = Currency.chaos
        price_info.price_history = price_history
        price_info.price_history_currency = Currency.chaos


async def main():
    await connect_to_mongodb(document_models)

    start = time.perf_counter()
    total_items = await Item.count()

    # * bounded queue ensures we only produce and consume data as needed
    items_queue: Queue[list[ItemRecord] | None] = Queue(maxsize=1)
    price_history_queue: Queue[dict[Any, list[PriceHistoryEntity]] | None] = Queue()
    updated_items_queue: Queue[list[ItemRecord] | None] = Queue()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(push_items_to_queue(total_items, BATCH_SIZE, items_queue))
        tg.create_task(get_price_history_data(items_queue, price_history_queue))
        tg.create_task(manage_prediction_data(price_history_queue, updated_items_queue))
        tg.create_task(update_items_data(updated_items_queue))

    logger.info(f"time taken for script execution: {time.perf_counter() - start}")


if __name__ == "__main__":
    asyncio.run(main())
