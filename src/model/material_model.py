from functools import lru_cache
from math import ceil
from typing import Dict


FOUNDATION_HERB_ID = "foundation_herb"


def get_breakthrough_materials_for_step(realms_data: Dict, realm_name: str, level: int) -> Dict[str, int]:
    mats = realms_data.get("breakthrough_materials", {})
    realm_breakthrough = mats.get(realm_name, {})
    level_mats = realm_breakthrough.get(str(level), {})
    return {str(k): int(v) for k, v in level_mats.items()}


def calc_foundation_herb_needed(materials: Dict[str, int], recipes_data: Dict) -> int:
    recipes = recipes_data.get("recipes", {})

    @lru_cache(maxsize=None)
    def herbs_per_item(item_id: str) -> int:
        if item_id == FOUNDATION_HERB_ID:
            return 1
        recipe = recipes.get(item_id)
        if not recipe:
            return 0

        total = 0
        recipe_materials = recipe.get("materials", {})
        for mat_id, mat_count in recipe_materials.items():
            total += herbs_per_item(str(mat_id)) * int(mat_count)
        product_count = int(recipe.get("product_count", 1))
        if product_count <= 0:
            return 0
        return int(ceil(total / product_count))

    total_herb = 0
    for item_id, count in materials.items():
        total_herb += herbs_per_item(str(item_id)) * int(count)
    return int(total_herb)
