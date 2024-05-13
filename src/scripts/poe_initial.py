import asyncio
from dataclasses import dataclass
import json
import os
import time
from typing import Any

from httpx import AsyncClient, Client
from loguru import logger

from src.config.services import connect_to_mongodb
from src.models import document_models
from src.models.poe import Item, ItemCategory, ItemPrice


@dataclass
class Category:
    name: str
    internal_name: str
    enabled: bool = True


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
        Category("Maps", "UniqueWeapon"),
        Category("Blighted Maps", "UniqueArmour"),
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


async def get_and_map_data() -> dict[str, list[dict]]:
    category_items_mapping = {}

    async with AsyncClient(base_url="https://poe.ninja/api/data") as client:
        for _, categories in CATEGORY_GROUP_MAP.items():
            for category in categories:
                internal_category_name = category.internal_name
                category_name = category.name

                res = await client.get(f"/itemoverview?league=Necropolis&type={category.internal_name}")
                logger.debug(f"category: {internal_category_name}, status_code: {res.status_code}")

                data: list[dict] = res.json()["lines"]
                category_items_mapping[category_name] = data

                time.sleep(0.1)

    return category_items_mapping


async def main():
    await connect_to_mongodb(document_models)
    # await save_update_categories()
    category_items_mapping = await get_and_map_data()


if __name__ == "__main__":
    asyncio.run(main())
