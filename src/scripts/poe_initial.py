import asyncio
from dataclasses import dataclass
import json
import os
import time
from typing import Any, cast

from httpx import AsyncClient, Client
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


async def save_update_categories():
    for group, categories in CATEGORY_GROUP_MAP.items():
        for category in categories:
            item_category = ItemCategory(name=category.name, internal_name=category.internal_name, group=group)
            await ItemCategory.save(item_category)


def write_item_data_to_disk(group: str, category_name: str, data: dict[str, Any]):
    base_path = f"itemData/{group}"
    file_path = f"{base_path}/{category_name}.json"

    if os.path.exists(file_path):
        logger.info(f"{file_path} exists, skipping...")
        return

    os.makedirs(f"{base_path}", exist_ok=True)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


async def get_item_data() -> dict[str, list[dict]]:
    category_item_mapping = {}

    async with AsyncClient(base_url="https://poe.ninja/api/data") as client:
        for _, categories in CATEGORY_GROUP_MAP.items():
            for category in categories:
                internal_category_name = category.internal_name
                category_name = category.name

                logger.debug(f"fetching data for {category_name}")

                api_endpoint = "currencyoverview" if internal_category_name == "Currency" else "itemoverview"
                url = f"/{api_endpoint}?league=Necropolis&type={category.internal_name}"
                res = await client.get(url)
                logger.debug(f"category: {internal_category_name}, status_code: {res.status_code}")

                # TODO: parse and pass currency icons separately
                item_data: list[dict] = res.json()["lines"]
                category_item_mapping[category_name] = item_data

                time.sleep(0.1)

    return category_item_mapping


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
    await save_update_categories()
    category_items_mapping = await get_item_data()
    await save_item_data(category_items_mapping)


if __name__ == "__main__":
    asyncio.run(main())
