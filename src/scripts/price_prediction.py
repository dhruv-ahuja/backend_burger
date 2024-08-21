import asyncio
from asyncio import Queue
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
from src.models.poe import Item, ItemCategory
from src.schemas.poe import Currency, ItemPrice

# TODO: handle extreme decimal case scenarios for items like Mirror of Kalandra

API_BASE_URL = "https://poe.ninja/api/data"
BATCH_SIZE = 500
LEAGUE = "Settlers"


# schema logic
def round_off_price(value: float):
    return round(Decimal(value), 2)


class PriceHistoryEntity(BaseModel):
    count: int
    value: Annotated[Decimal, BeforeValidator(round_off_price)]
    days_ago: int = Field(alias="daysAgo")

    def convert_days_ago_to_date(self):
        now = dt.datetime.now(dt.UTC)
        return now - dt.timedelta(self.days_ago)


async def get_and_map_categories() -> dict[str, ItemCategory]:
    """Gets and maps category model instances to their Ids."""

    try:
        categories = await ItemCategory.find_all().to_list()
    except Exception as exc:
        logger.error(f"error getting item categories: {exc}")
        raise

    category_map = {category.internal_name: category for category in categories}
    return category_map


async def get_items(offset: int, limit: int) -> list[Item]:
    """Gets all Items from the database."""

    try:
        # avoiding links here as each object will fetch its own category record
        return await Item.find_all(skip=offset, limit=limit).to_list()
    except Exception as exc:
        logger.error(f"error getting items with offset {offset}: {exc}")
        raise


async def push_items_to_queue(total_items: int, batch_size: int, items_queue: Queue[list[Item] | None]) -> None:
    """Gets and pushes item data to queue. `items_queue` being a bounded queue ensures that this function only
    gets data from the database when necessary."""

    start = time.perf_counter()
    offset = 0

    while offset < total_items:
        items = await get_items(offset, batch_size)
        await items_queue.put(items)

        offset += batch_size
        logger.info(f"pushed items data till offset {offset}")

    # push sentinel value
    await items_queue.put(None)

    logger.info(f"time taken to get and push items to queue: {time.perf_counter() - start}; offset: {offset}")


async def prepare_api_data(
    item: Item, price_history_map: dict[Any, list[PriceHistoryEntity]], client: AsyncClient
) -> None:
    """Helper function to get and prepare Price History API data, and add it to the provided hashmap."""

    item_id = item.poe_ninja_id
    category = item.category

    print(f"running for {item_id}, {category}")

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
        print(API_BASE_URL + "/" + url)
        price_history_api_data = []

    try:
        if isinstance(price_history_api_data, dict):
            price_history_api_data = price_history_api_data.pop("receiveCurrencyGraphData")
        ta = TypeAdapter(list[PriceHistoryEntity])
        price_history_data = ta.validate_python(price_history_api_data)
    except pydantic.ValidationError as exc:
        logger.error(
            f"error parsing price history data for item_id {item_id} belonging to '{category}' category: {exc}"
        )
        price_history_data = []

    print(f"ran for {item_id}, {category}")
    price_history_map[item.id] = price_history_data


async def get_price_history_data(
    items_queue: Queue[list[Item] | None], price_history_queue: Queue[dict[Any, list[PriceHistoryEntity]] | None]
) -> None:
    """Gets all available price history data for the available items, and parses them into a consistent schema.
    Maps and pushes the data into a queue for futher processing."""

    price_history_map = {}

    while True:
        items = await items_queue.get()
        if items is None:
            # signal end of production
            await price_history_queue.put(None)
            return

        start = time.perf_counter()
        offset = 0
        limit = 5
        total_items = len(items[:30])  # TODO: revert this!

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
    price_history_queue: Queue[dict[Any, list[PriceHistoryEntity]] | None],
    price_prediction_queue: Queue[dict[Any, list[ndarray]] | None],
) -> None:
    """Manages the flow of incoming price history queue data, predicting future prices based on that, and adds that to
    the price prediction queue. Ensures that data is available for consumption down the chain."""

    price_prediction_map = {}
    # offset = 0

    # push both price history queue and price_prediction items in one go, to make both the data sets available for saving into the db

    while True:
        price_history_map = await price_history_queue.get()
        if price_history_map is None:
            # signal end of production
            await price_prediction_queue.put(None)
            return

        i = 0
        start = time.perf_counter()
        for item_id, price_history_data in price_history_map.items():
            if i != 30:
                price_prediction_data = predict_future_item_prices(price_history_data)

                price_prediction_map[item_id] = price_history_data
                print(item_id, price_prediction_data)

                i += 1

        await price_prediction_queue.put(price_prediction_map)
        logger.debug(f"time taken to predict for current batch: {time.perf_counter() - start}")


async def update_items_data(items: list[Item], iteration_count: int) -> None:
    """Bulk-updates item data in the database. Serializes item price schema into a JSON object for insertion into
    the database. Creates an order of Pymongo-native `UpdateOne` operations and bulk writes them for efficiency over
    inserting each record one-by-one."""

    bulk_operations = []
    item_collection: motor.motor_asyncio.AsyncIOMotorCollection = Item.get_motor_collection()  # type: ignore

    for item in items:
        serialized_data = item.price_info.serialize() if item.price_info else {}

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
        logger.info(f"result from batch number {iteration_count}'s bulk update: {result}")
    except Exception as exc:
        logger.error(f"error bulk writing: {exc}")
        logger.error(f"{type(exc)}")


async def main_old():
    offset = iteration_count = 0

    await connect_to_mongodb(document_models)

    start = time.perf_counter()
    category_map = await get_and_map_categories()

    item_price_history_data = []
    item_price_prediction_data = []

    total_items = await Item.count()

    # initiate requisite queues
    # bounded queue ensures we only load data as needed
    items_queue: Queue[list[Item] | None] = Queue(maxsize=1)

    while offset < total_items:
        s = batch_start = time.perf_counter()
        items = await get_items(offset, BATCH_SIZE)
        t = time.perf_counter()
        print(f"{t -s} to fetch items till {offset}")

        for item in items[:20]:
            s2 = time.perf_counter()
            category_key = item.category if item.category else ""
            try:
                item_category = category_map[category_key]
            except KeyError:
                logger.error(f"item category not found for '{item.name}' item")
                continue

            price_history_data = await get_price_history_data(item_category.internal_name, item.poe_ninja_id)

            item_price_history_data.append(price_history_data)

            print(f"{time.perf_counter() - s2} to fetch price hisotry data")

            s2 = time.perf_counter()

            price_predictions = predict_future_item_prices(price_history_data)
            item_price_prediction_data.append(price_predictions)

            print(f"{time.perf_counter() - s2} to predict future data")

            s2 = time.perf_counter()
            await add_item_price_data(items, price_history_data, item_price_prediction_data)

            print(f"{time.perf_counter() - s2} for updating data")

        await update_items_data(items, iteration_count)
        batch_stop = time.perf_counter()

        logger.info(
            f"time taken for price predictions for batch {iteration_count + 1} of items: {batch_stop - batch_start}"
        )

        offset += BATCH_SIZE
        iteration_count += 1

        break

    stop = time.perf_counter()
    logger.info(f"total time taken for predicting prices of {total_items}: {stop - start}")


async def func(q: Queue):
    await asyncio.sleep(2)
    i = await q.get()
    while i is not None:
        logger.info("going 2 sleep")
        await asyncio.sleep(1)
        i = await q.get()


async def main():
    await connect_to_mongodb(document_models)

    start = time.perf_counter()
    total_items = await Item.count()

    # TODO: remove this function
    # category_map = await get_and_map_categories()

    # * bounded queue ensures we only load data as needed
    items_queue: Queue[list[Item] | None] = Queue(maxsize=1)
    price_history_queue: Queue[dict[Any, list[PriceHistoryEntity]] | None] = Queue()
    price_prediction_queue: Queue[dict[Any, list[ndarray]] | None] = Queue()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(push_items_to_queue(total_items, BATCH_SIZE, items_queue))
        # tg.create_task(func(items_queue))
        tg.create_task(get_price_history_data(items_queue, price_history_queue))
        tg.create_task(manage_prediction_data(price_history_queue, price_prediction_queue))

    logger.warning(f"time taken for full flow: {time.perf_counter() - start}")


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

        # TODO: check for low confidence
        item_price_data = ItemPrice(
            chaos_price=todays_price_data.value,
            price_history=price_history_mapping,
            price_history_currency=Currency.chaos,
            price_prediction=price_prediction_mapping,
            price_prediction_currency=Currency.chaos,
        )
        item.price_info = item_price_data


if __name__ == "__main__":
    asyncio.run(main())
