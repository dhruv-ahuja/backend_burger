import asyncio
from dataclasses import dataclass


from src.config.services import connect_to_mongodb
from src.models import document_models
from src.models.poe import Item, ItemCategory, ItemGroup, ItemPrice


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
        Category("Beasts", "Beasts"),
        Category("Essences", "Essence"),
        Category("Vials", "Vial"),
    ],
}


async def save_update_categories():
    for group, categories in CATEGORY_GROUP_MAP.items():
        for category in categories:
            item_category = ItemCategory(name=category.name, internal_name=category.internal_name, group=group)
            await ItemCategory.save(item_category)


async def main():
    await connect_to_mongodb(document_models)
    await save_update_categories()


if __name__ == "__main__":
    asyncio.run(main())
