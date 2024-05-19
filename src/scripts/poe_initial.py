import asyncio
from asyncio import Queue
from dataclasses import dataclass
import json
import os
import time
from typing import Any, cast

from httpx import AsyncClient, RequestError
from loguru import logger
from pydantic import BaseModel, Field
import pydantic

from src.config.services import connect_to_mongodb
from src.models import document_models
from src.models.poe import Item, ItemCategory, ItemIdType


@dataclass
class Category:
    name: str
    internal_name: str
    enabled: bool = True


# * these encapsulate required currency and item data for each entry from API responses
class CurrencyItemEntity(BaseModel):
    class Pay(BaseModel):
        pay_currency_id: int

    class Receive(BaseModel):
        get_currency_id: int

    currencyTypeName: str
    pay: Pay | None = None
    receive: Receive | None = None


class ItemEntity(BaseModel):
    id_: int = Field(alias="id")
    name: str
    baseType: str
    variant: str | None = None
    icon: str
    itemType: str | None = None


CATEGORY_GROUP_MAP = {
    "Currency": [
        Category("Currency", "Currency"),
        Category("Fragments", "Fragment"),
        Category("Coffins", "Coffin"),
        Category("Allflame Embers", "AllflameEmber"),
        Category("Tattoos", "Tattoo"),
        Category("Omens", "Omen"),
        Category("Divination Cards", "DivinationCard"),
        Category("Artifacts", "Artifact"),
        Category("Oils", "Oil"),
        Category("Incubators", "Incubator"),
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


async def save_item_categories():
    """Iterates over the nested category group hashmap and Saves information for individual item categories into the
    database."""

    for group, categories in CATEGORY_GROUP_MAP.items():
        for category in categories:
            item_category = ItemCategory(name=category.name, internal_name=category.internal_name, group=group)
            await ItemCategory.save(item_category)


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


async def prepare_api_data(api_item_data_queue: Queue[tuple[ItemCategory, list[dict]]], item_data_queue: Queue[Item]):
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

                logger.debug(f"pushed api data for {category_name}; {api_item_data_payload[1][:2]}")

                await parse_api_item_data(api_item_data_queue, item_data_queue)


async def get_category_by_name(name: str) -> ItemCategory | None:
    """Gets an `ItemCategory` document from the database by its name."""

    try:
        category_record = await ItemCategory.find(ItemCategory.name == name).first_or_none()
    except Exception as exc:
        logger.error(f"error getting category by name '{name}': {exc} ")
        return

    return category_record


async def get_item_api_data(internal_category_name: str, client: AsyncClient) -> list[dict[str, Any]]:
    """Gets data for all Items belonging to a category from the apt Poe Ninja API by preparing and calling the API
    endpoint, then parsing and returning the item data for the category."""

    api_endpoint = "currencyoverview" if internal_category_name == "Currency" else "itemoverview"
    url = f"/{api_endpoint}?league=Necropolis&type={internal_category_name}"

    try:
        response = await client.get(url)
        logger.debug(f"category: {internal_category_name}, status_code: {response.status_code}")
    except RequestError as exc:
        logger.error(f"error fetching data for '{internal_category_name}' with endpoint '{api_endpoint}': {exc}")
        item_data = []
    else:
        # TODO: parse and pass currency icons separately
        item_data: list[dict] = response.json()["lines"]

    return item_data


# TODO: this should run concurrently with the other tasks
async def parse_api_item_data(
    api_item_data_queue: Queue[tuple[ItemCategory, list[dict]]], item_data_queue: Queue[Item]
) -> None:
    """Fetches item API data from the respective queue, and parses it into apt Pydantic model instances, hence
    structuring each item in the list and validating its values.
    Pushes the structured data records to the item data queue once done."""

    category_record, api_item_data = await api_item_data_queue.get()

    category_name = category_record.name
    category_internal_name = category_record.internal_name

    is_currency = category_internal_name == "Currency"
    logger.debug(f"received item data for {category_name}, parsing into pydantic instances")

    for api_item_entity in api_item_data:
        try:
            item_entity = CurrencyItemEntity(**api_item_entity) if is_currency else ItemEntity(**api_item_entity)
        except pydantic.ValidationError as exc:
            if is_currency:
                name = api_item_entity.get("currencyTypeName")
                item_type = "currency"
            else:
                name = api_item_entity.get("name")
                item_type = "item"

            logger.error(f"error parsing '{name}' {item_type} entity data: {exc}")
            continue

        if is_currency:
            item_entity = cast(CurrencyItemEntity, item_entity)
            id_type = None

            if item_entity.pay is not None:
                poe_ninja_id = item_entity.pay.pay_currency_id
                id_type = ItemIdType.pay
            elif item_entity.receive is not None:
                poe_ninja_id = item_entity.receive.get_currency_id
                id_type = ItemIdType.receive
            else:
                logger.error(f"no pay or get id found for {item_entity.currencyTypeName}, skipping")
                continue

            item_record = Item(
                poe_ninja_id=poe_ninja_id,
                id_type=id_type,
                name=item_entity.currencyTypeName,
                category=category_record,  # type: ignore
                type_=None,
            )

        else:
            item_entity = cast(ItemEntity, item_entity)
            item_record = Item(
                poe_ninja_id=item_entity.id_,
                name=item_entity.name,
                type_=item_entity.itemType,
                category=category_record,  # type: ignore
                icon_url=item_entity.icon,
                variant=item_entity.variant,
            )

        await item_data_queue.put(item_record)

    logger.debug(f"parsed all entities for {category_name}")


# TODO: create asyncio tasks and divide categories' data into separate threads for concurrent insertions;
# TODO: divide Base Types into several tasks due to large size (~20k)
async def save_item_data(category_item_mapping: dict[str, list[dict]]) -> None:
    logger.debug("starting to save item data in DB")
    items = []

    for category, item_data in category_item_mapping.items():
        start = time.perf_counter()
        logger.debug(f"serializing data for {category}")

        category_record = await ItemCategory.find(ItemCategory.name == category).first_or_none()
        if category_record is None:
            logger.error(f"DB record for {category} wasn't found!")
            continue

        is_currency = category == "Currency"

        for entity in item_data:
            try:
                if is_currency:
                    item_entity = CurrencyItemEntity(**entity)
                else:
                    item_entity = ItemEntity(**entity)

            except pydantic.ValidationError as exc:
                if is_currency:
                    name = entity["currencyTypeName"]
                    item_type = "currency"
                else:
                    name = entity["name"]
                    item_type = "item"

                logger.error(f"error parsing '{name}' {item_type} entity data: {exc}")
                continue

            if is_currency:
                item_entity = cast(CurrencyItemEntity, item_entity)
                id_type = None

                if item_entity.pay is not None:
                    poe_ninja_id = item_entity.pay.pay_currency_id
                    id_type = ItemIdType.pay
                elif item_entity.receive is not None:
                    poe_ninja_id = item_entity.receive.get_currency_id
                    id_type = ItemIdType.receive
                else:
                    logger.error(f"no pay or get id found for {item_entity.currencyTypeName}, skipping")
                    continue

                item_record = Item(
                    poe_ninja_id=poe_ninja_id,
                    id_type=id_type,
                    name=item_entity.currencyTypeName,
                    category=category_record,  # type: ignore
                    type_=None,
                )

            else:
                item_entity = cast(ItemEntity, item_entity)
                item_record = Item(
                    poe_ninja_id=item_entity.id_,
                    name=item_entity.name,
                    type_=item_entity.itemType,
                    category=category_record,  # type: ignore
                    icon_url=item_entity.icon,
                    variant=item_entity.variant,
                )

            items.append(item_record)

    await Item.insert_many(items)
    stop = time.perf_counter()
    execution_time = stop - start

    logger.debug(f"time taken for category: {category}: {execution_time}")


async def main():
    await connect_to_mongodb(document_models)
    await save_item_categories()

    api_item_data_queue: Queue[tuple[ItemCategory, list[dict]]] = Queue()
    item_data_queue: Queue[Item] = Queue()  # TODO: add queue size limit

    await prepare_api_data(api_item_data_queue, item_data_queue)

    # await save_item_data(category_items_mapping)


if __name__ == "__main__":
    asyncio.run(main())
