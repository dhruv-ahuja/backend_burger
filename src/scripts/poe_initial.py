import asyncio
from asyncio import Queue
from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
import json
import os
import time
from typing import Any, cast

import beanie
import beanie.operators
from httpx import AsyncClient, RequestError
from loguru import logger
from pydantic import BaseModel, Field, computed_field
import pydantic

from src.config.services import connect_to_mongodb
from src.models import document_models
from src.models.poe import Item, ItemCategory
from src.schemas.poe import ItemIdType, ItemPrice


@dataclass
class Category:
    name: str
    internal_name: str
    enabled: bool = True


@dataclass
class ApiItemData:
    item_data: list[dict[str, Any]]
    currency_item_metadata: list[dict[str, Any]]


# * these encapsulate required currency and item data for each entry from API responses
class ItemSparkline(BaseModel):
    data: list[Decimal | None]
    totalChange: Decimal | None


class CurrencyItemMetadata(BaseModel):
    id_: int = Field(alias="id")
    icon: str | None = None


class CurrencyItemEntity(BaseModel):
    class Pay(BaseModel):
        pay_currency_id: int
        listing_count: int = 0

    class Receive(BaseModel):
        get_currency_id: int
        listing_count: int = 0

    currencyTypeName: str
    pay: Pay | None = None
    receive: Receive | None = None
    metadata: CurrencyItemMetadata | None = None
    chaosEquivalent: Decimal = Decimal(0)


class ItemEntity(BaseModel):
    id_: int = Field(alias="id")
    name: str
    baseType: str
    variant: str | None = None
    icon: str
    itemType: str | None = None
    chaosValue: Decimal = Decimal(0)
    divineValue: Decimal = Decimal(0)
    links: int | None = None
    listingCount: int = 0
    sparkline: ItemSparkline
    lowConfidenceSparkline: ItemSparkline

    @computed_field
    @property
    def low_confidence(self) -> bool:
        low_confidence = False

        if len(self.sparkline.data) < 3 or self.listingCount < 10 and len(self.lowConfidenceSparkline.data) > 3:
            low_confidence = True

        return low_confidence


CATEGORY_GROUP_MAP = {
    "Currency": [
        Category("Currency", "Currency"),
        Category("Fragments", "Fragment"),
        Category("Allflame Embers", "AllflameEmber"),
        Category("Tattoos", "Tattoo"),
        Category("Omens", "Omen"),
        Category("Divination Cards", "DivinationCard"),
        Category("Artifacts", "Artifact"),
        Category("Oils", "Oil"),
        Category("Incubators", "Incubator"),
        Category("Kalguuran Runes", "KalguuranRune"),
    ],
    "EquipmentAndGems": [
        Category("Unique Weapons", "UniqueWeapon"),
        Category("Unique Armours", "UniqueArmour"),
        Category("Unique Accessories", "UniqueAccessory"),
        Category("Unique Flasks", "UniqueFlask"),
        Category("Unique Jewels", "UniqueJewel"),
        Category("Unique Relics", "UniqueRelic"),
        Category("Skill Gems", "SkillGem"),
        Category("Cluster Jewels", "ClusterJewel"),
    ],
    "Atlas": [
        Category("Maps", "Map"),
        Category("Blighted Maps", "BlightedMap"),
        Category("Blight-ravaged Maps", "BlightRavagedMap"),
        Category("Scourged Maps", "ScourgedMap"),
        Category("Unique Maps", "UniqueMap"),
        Category("Delirium Orbs", "DeliriumOrb"),
        Category("Invitations", "Invitation"),
        Category("Scarabs", "Scarab"),
        Category("Memories", "Memory"),
    ],
    "Crafting": [
        Category("Base Types", "BaseType"),
        Category("Fossils", "Fossil"),
        Category("Resonators", "Resonator"),
        Category("Beasts", "Beast"),
        Category("Essences", "Essence"),
        Category("Vials", "Vial"),
    ],
}

CATEGORY_GROUP_API_URL_MAP = {
    "Currency": "currencyOverview",
    "EquipmentAndGems": "itemOverview",
    "Atlas": "itemOverview",
    "Crafting": "currencyOverview",
}


API_BASE_URL = "https://poe.ninja/api/data"
BATCH_INSERT_LIMIT = 15_000
LEAGUE = "Settlers"


async def save_item_categories():
    """Iterates over the nested category group hashmap and Saves information for individual item categories into the
    database."""

    for group, categories in CATEGORY_GROUP_MAP.items():
        for category in categories:
            await ItemCategory.find_one(ItemCategory.name == category.name).upsert(
                beanie.operators.Set({ItemCategory.updated_time: dt.datetime.now(dt.UTC)}),
                on_insert=ItemCategory(name=category.name, internal_name=category.internal_name, group=group),
            )  # type: ignore


def write_item_data_to_disk(group: str, category_name: str, data: dict[str, Any]):
    """Writes item API data to disk, using the group and category names to define the JSON file path."""

    base_path = f"itemData/{group}"
    file_path = f"{base_path}/{category_name}.json"

    if os.path.exists(file_path):
        logger.info(f"{file_path} exists, skipping...")
        return

    os.makedirs(f"{base_path}", exist_ok=True)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


async def prepare_api_data(api_item_data_queue: Queue[tuple[ItemCategory, ApiItemData] | None]):
    start = time.perf_counter()
    async with AsyncClient(base_url=API_BASE_URL) as client:
        for _, categories in CATEGORY_GROUP_MAP.items():
            for category in categories:
                internal_category_name = category.internal_name
                category_name = category.name

                category_record = await get_category_by_name(category_name)
                if category_record is None:
                    logger.error(f"DB record for {category.name} wasn't found, skipping process!")
                    continue

                logger.debug(f"getting api data for {category_name}")
                api_item_data = await get_item_api_data(internal_category_name, client)

                api_item_data_payload = (category_record, api_item_data)
                await api_item_data_queue.put(api_item_data_payload)

                logger.debug(f"pushed api data for {category_name}")

        # push sentinel value to indicate end of production
        await api_item_data_queue.put(None)

    stop = time.perf_counter()
    logger.info(f"total execution time for preparing api data: {stop - start}")


async def get_category_by_name(name: str) -> ItemCategory | None:
    """Gets an `ItemCategory` document from the database by its name."""

    try:
        category_record = await ItemCategory.find(ItemCategory.name == name).first_or_none()
    except Exception as exc:
        logger.error(f"error getting category by name '{name}': {exc} ")
        return

    return category_record


async def get_item_api_data(internal_category_name: str, client: AsyncClient) -> ApiItemData:
    """Gets data for all Items belonging to a category from the apt Poe Ninja API by preparing and calling the API
    endpoint, then parsing and returning the item data for the category."""

    api_endpoint = "currencyoverview" if internal_category_name in ["Currency", "Fragment"] else "itemoverview"
    url = f"/{api_endpoint}?league={LEAGUE}&type={internal_category_name}"

    item_data = []
    currency_item_metadata = []

    try:
        response = await client.get(url)
        logger.debug(f"category: {internal_category_name}, status_code: {response.status_code}")
    except RequestError as exc:
        logger.error(f"error fetching data for '{internal_category_name}' with endpoint '{api_endpoint}': {exc}")
    else:
        json_response = response.json()
        item_data: list[dict] = json_response["lines"]
        if len(item_data) < 2:
            logger.error(f"no data found for '{internal_category_name}' with endpoint: '{api_endpoint}'")

        currency_item_metadata: list[dict] = json_response.get("currencyDetails", [])

    api_item_data = ApiItemData(item_data, currency_item_metadata)
    return api_item_data


def map_currency_icon_urls(currency_item_metadata: list[dict[str, Any]]) -> dict[int, CurrencyItemMetadata]:
    """Maps a list of currency item metadata to each records' ID."""

    currency_item_mapping = {}

    for data in currency_item_metadata:
        try:
            entry = CurrencyItemMetadata(**data)
            currency_item_mapping[entry.id_] = entry
        except pydantic.ValidationError as exc:
            logger.error(f"error parsing currency icon data ({data}) into schema: {exc}")
            continue

    return currency_item_mapping


def parse_api_entity(
    api_item_entity: dict[str, Any], is_currency: bool, currency_item_metadata: list[dict[str, Any]]
) -> CurrencyItemEntity | ItemEntity | None:
    """Parse API Entity data into respective Currency or ItemEntity instances, adding currency item metadata
    for items under the currency group, if metadata is available."""

    item_entity = None
    currency_item_mapping = map_currency_icon_urls(currency_item_metadata)

    try:
        if is_currency:
            item_entity = CurrencyItemEntity(**api_item_entity)

            if item_entity.pay and item_entity.pay.pay_currency_id:
                currency_item_id = item_entity.pay.pay_currency_id
            elif item_entity.receive and item_entity.receive.get_currency_id:
                currency_item_id = item_entity.receive.get_currency_id

            api_item_metadata = currency_item_mapping.get(currency_item_id)
            item_entity.metadata = api_item_metadata
        else:
            item_entity = ItemEntity(**api_item_entity)
    except pydantic.ValidationError as exc:
        if is_currency:
            name = api_item_entity.get("currencyTypeName")
            item_type = "currency"
        else:
            name = api_item_entity.get("name")
            item_type = "item"

        logger.error(f"error parsing '{name}' {item_type} entity data: {exc}")

    return item_entity


def prepare_item_record(
    item_entity: CurrencyItemEntity | ItemEntity, category_record: ItemCategory, is_currency: bool
) -> Item | None:
    """Prepares item record by assigning parsed data to the DB model instance. Skips instantiating currency records if
    neither pay or get IDs are available to act as an identifier."""

    if is_currency:
        item_entity = cast(CurrencyItemEntity, item_entity)
        id_type = None

        if item_entity.pay is not None:
            poe_ninja_id = item_entity.pay.pay_currency_id
            id_type = ItemIdType.pay
            listings = item_entity.pay.listing_count
        elif item_entity.receive is not None:
            poe_ninja_id = item_entity.receive.get_currency_id
            id_type = ItemIdType.receive
            listings = item_entity.receive.listing_count
        else:
            logger.error(f"no pay or get id found for {item_entity.currencyTypeName}, skipping")
            return

        price_info = ItemPrice(chaos_price=item_entity.chaosEquivalent, listings=listings)

        item_metadata = item_entity.metadata
        item_record = Item(
            poe_ninja_id=poe_ninja_id,
            id_type=id_type,
            name=item_entity.currencyTypeName,
            type_=None,
            category=category_record.internal_name,
            icon_url=item_metadata.icon if item_metadata else None,
            price_info=price_info,
        )

    else:
        item_entity = cast(ItemEntity, item_entity)

        price_info = ItemPrice(
            chaos_price=item_entity.chaosValue,
            divine_price=item_entity.divineValue,
            listings=item_entity.listingCount,
            low_confidence=item_entity.low_confidence,
        )
        # TODO: save baseType too
        item_record = Item(
            poe_ninja_id=item_entity.id_,
            name=item_entity.name,
            type_=item_entity.itemType,
            category=category_record.internal_name,
            icon_url=item_entity.icon,
            variant=item_entity.variant,
            links=item_entity.links,
            price_info=price_info,
        )

    return item_record


async def parse_api_item_data(
    api_item_data_queue: Queue[tuple[ItemCategory, ApiItemData] | None], item_data_queue: Queue[list[Item] | None]
) -> None:
    """Fetches item API data from the respective queue, and parses it into apt Pydantic model instances, hence
    structuring each item in the list and validating its values.
    Pushes the structured data records to the item data queue once done."""

    item_records: list[Item] = []

    start = time.perf_counter()
    while True:
        api_item_data_payload = await api_item_data_queue.get()

        if api_item_data_payload is None:
            # no more data to process, push current item data, sentinel value and exit
            await item_data_queue.put(item_records)
            await item_data_queue.put(None)
            break

        category_record, api_item_data = api_item_data_payload
        category_name = category_record.name
        category_internal_name = category_record.internal_name

        is_currency = category_internal_name in ["Currency", "Fragment"]
        currency_item_metadata = api_item_data.currency_item_metadata

        logger.debug(f"received item data for {category_name}, parsing into pydantic instances")

        for api_item_entity in api_item_data.item_data:
            item_entity = parse_api_entity(api_item_entity, is_currency, currency_item_metadata)
            if item_entity is None:
                continue

            item_record = prepare_item_record(item_entity, category_record, is_currency)
            if item_record is None:
                continue

            item_records.append(item_record)

            # push this batch of item records and reset the list container
            if len(item_records) >= BATCH_INSERT_LIMIT:
                await item_data_queue.put(item_records)
                item_records = []

        logger.debug(f"parsed all entities for {category_name}")

    stop = time.perf_counter()
    logger.info(f"total execution time for parsing api data: {stop - start}")


async def save_items(item_records: list[Item]) -> bool:
    """Saves a list of Item records to the database."""

    try:
        await Item.insert_many(item_records)
    except Exception as exc:
        logger.error(f"error saving item records to DB: {exc}")
        return False

    return True


async def save_item_data(item_data_queue: Queue[list[Item] | None]) -> None:
    """Gets item records in bulk from the item data queue and saves them to the database."""

    batch_save_count = 1
    logger.debug("initiating saving items to DB")

    start = time.perf_counter()
    while True:
        item_records = await item_data_queue.get()
        if item_records is None:
            logger.debug("consumer received exit signal")
            break

        logger.debug(f"saving batch {batch_save_count} of items to DB")
        save_was_success = await save_items(item_records)

        if save_was_success:
            logger.debug(f"successfully saved batch {batch_save_count} of items to DB")
        else:
            logger.debug(f"failed to save batch {batch_save_count} of items to DB")

        batch_save_count += 1

    stop = time.perf_counter()
    logger.info(f"time taken to save all records to DB: {stop - start}")


async def main():
    await connect_to_mongodb(document_models)
    await save_item_categories()

    api_item_data_queue: Queue[tuple[ItemCategory, ApiItemData] | None] = Queue()
    item_data_queue: Queue[list[Item] | None] = Queue()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(prepare_api_data(api_item_data_queue))
        tg.create_task(parse_api_item_data(api_item_data_queue, item_data_queue))
        tg.create_task(save_item_data(item_data_queue))


if __name__ == "__main__":
    asyncio.run(main())
