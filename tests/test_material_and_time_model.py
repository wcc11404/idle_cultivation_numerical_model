from src.model.material_model import calc_foundation_herb_needed, get_breakthrough_materials_for_step
from src.model.time_model import build_time_rows


def test_calc_foundation_herb_needed_recursive():
    recipes = {
        "recipes": {
            "foundation_pill": {
                "materials": {"foundation_herb": 3},
                "product_count": 1,
            },
            "golden_core_pill": {
                "materials": {"foundation_pill": 2, "foundation_herb": 1},
                "product_count": 1,
            },
        }
    }
    materials = {"golden_core_pill": 1}
    assert calc_foundation_herb_needed(materials, recipes) == 7


def test_calc_foundation_herb_needed_high_tier_recipe_non_zero():
    recipes = {
        "recipes": {
            "foundation_pill": {"materials": {"foundation_herb": 3}, "product_count": 1},
            "golden_core_pill": {
                "materials": {"foundation_pill": 3, "foundation_herb": 1},
                "product_count": 1,
            },
            "nascent_soul_pill": {
                "materials": {"golden_core_pill": 3, "foundation_herb": 1},
                "product_count": 1,
            },
        }
    }
    assert calc_foundation_herb_needed({"nascent_soul_pill": 1}, recipes) > 0


def test_get_breakthrough_materials_prefers_level_breakthrough_level10():
    realms_data = {
        "breakthrough_materials": {
            "筑基期": {
                "10": {"golden_core_pill": 1},
            }
        },
    }
    mats = get_breakthrough_materials_for_step(realms_data, "筑基期", 10)
    assert mats == {"golden_core_pill": 1}


def test_get_breakthrough_materials_uses_flat_level_entries():
    realms_data = {
        "breakthrough_materials": {
            "筑基期": {
                "3": {"foundation_pill": 1},
                "6": {"foundation_pill": 1},
                "9": {"foundation_pill": 2},
            }
        },
    }
    assert get_breakthrough_materials_for_step(realms_data, "筑基期", 3) == {"foundation_pill": 1}
    assert get_breakthrough_materials_for_step(realms_data, "筑基期", 6) == {"foundation_pill": 1}
    assert get_breakthrough_materials_for_step(realms_data, "筑基期", 9) == {"foundation_pill": 2}


def test_build_time_rows_units_and_cumulative():
    realms_data = {
        "realm_order": ["炼气期"],
        "breakthrough_materials": {
            "炼气期": {"1": {"foundation_pill": 1}},
        },
        "realms": {
            "炼气期": {
                "max_level": 2,
                "next_realm": "",
                "spirit_gain_speed": 1.0,
                "level_names": {"1": "一层", "2": "二层"},
                "levels": {
                    "1": {"spirit_energy_cost": 3600, "max_spirit_energy": 3600},
                    "2": {"spirit_energy_cost": 0, "max_spirit_energy": 0},
                },
            }
        },
    }
    recipes_data = {
        "recipes": {
            "foundation_pill": {"materials": {"foundation_herb": 3}, "product_count": 1}
        }
    }

    rows = build_time_rows(realms_data, recipes_data)
    assert len(rows) == 1
    row = rows[0]
    assert abs(row["step_spirit_hours"] - 1.0) < 1e-9
    assert abs(row["step_material_hours"] - 2.4) < 1e-9
    assert abs(row["cumulative_spirit_days"] - (1.0 / 24.0)) < 1e-9
    assert abs(row["cumulative_material_days"] - 0.1) < 1e-9
