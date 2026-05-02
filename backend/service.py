from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from src.io.data_paths import AREAS_PATH, ENEMIES_PATH, ITEMS_PATH, REALMS_PATH, RECIPES_PATH, SPELLS_PATH
from src.io.data_sync import ensure_local_data, sync_from_server
from src.io.json_store import load_json, save_json
from src.io.realms_text_updater import save_realms_numeric_fields_preserve_format
from src.model.battle_model import (
    DEFAULT_BATTLE_INTERVAL_SECONDS,
    DEFAULT_K_VALUE,
    DEFAULT_MAX_FIGHTS_PER_TRIAL,
    DEFAULT_TRIALS,
    FIXED_BATTLE_RANDOM_SEED,
    build_checkpoint_matrix,
    build_player_attrs_from_realm,
    build_tower_max_floor_by_stage,
    simulate_average,
)
from src.model.formatting import format_number
from src.model.realm_generator import apply_generation_rules
from src.model.time_model import build_time_rows_with_stone_gain

BREAKTHROUGH_RECIPE_CHAIN = [
    ("foundation_pill", ""),
    ("golden_core_pill", "foundation_pill"),
    ("nascent_soul_pill", "golden_core_pill"),
    ("spirit_separation_pill", "nascent_soul_pill"),
    ("void_refining_pill", "spirit_separation_pill"),
    ("body_integration_pill", "void_refining_pill"),
    ("mahayana_pill", "body_integration_pill"),
    ("tribulation_pill", "mahayana_pill"),
]

PAGE_META = [
    {"key": "cultivation", "label": "修炼建模可视化", "group": "建模页面"},
    {"key": "battle", "label": "战斗建模可视化", "group": "建模页面"},
    {"key": "areas", "label": "历练区域配置（areas）", "group": "配置工具"},
    {"key": "realms", "label": "境界配置（realms）", "group": "配置工具"},
    {"key": "enemies", "label": "敌人模板配置（enemies）", "group": "配置工具"},
    {"key": "recipes", "label": "丹方配置（recipes）", "group": "配置工具"},
    {"key": "spells", "label": "术法配置（spells）", "group": "配置工具"},
]


def get_meta_pages() -> list[dict[str, str]]:
    return PAGE_META


def load_all_configs() -> dict[str, Any]:
    ensure_local_data()
    return {
        "realms": load_json(REALMS_PATH),
        "recipes": load_json(RECIPES_PATH),
        "areas": load_json(AREAS_PATH),
        "enemies": load_json(ENEMIES_PATH),
        "items": load_json(ITEMS_PATH),
        "spells": load_json(SPELLS_PATH),
    }


def get_realms_payload() -> dict[str, Any]:
    realms_data = load_json(REALMS_PATH)
    return {
        "config": realms_data,
        "editor": {
            **_derive_default_params(realms_data),
            "lianqiRows": _get_lianqi_editor_rows(realms_data),
        },
    }


def save_realms_payload(editor: dict[str, Any]) -> dict[str, Any]:
    old_data = load_json(REALMS_PATH)
    draft = build_realms_draft(old_data, editor)
    save_realms_numeric_fields_preserve_format(REALMS_PATH, old_data, draft)
    return get_realms_payload()


def build_realms_draft(base_realms: dict[str, Any], editor: dict[str, Any]) -> dict[str, Any]:
    rows = editor["lianqiRows"]
    return apply_generation_rules(
        realms_data=deepcopy(base_realms),
        lianqi_healths={int(r["层级"]): int(r["health"]) for r in rows},
        lianqi_attacks={int(r["层级"]): int(r["attack"]) for r in rows},
        lianqi_defenses={int(r["层级"]): int(r["defense"]) for r in rows},
        lianqi_costs={int(r["层级"]): int(r["spirit_energy_cost"]) for r in rows},
        lianqi_stone_costs={int(r["层级"]): int(r["spirit_stone_cost"]) for r in rows},
        lianqi_max_spirits={int(r["层级"]): int(r["max_spirit_energy"]) for r in rows},
        foundation_base_health=int(editor["foundation_base_health"]),
        foundation_base_attack=int(editor["foundation_base_attack"]),
        foundation_base_defense=int(editor["foundation_base_defense"]),
        foundation_base_cost=int(editor["foundation_base_cost"]),
        foundation_base_stone_cost=int(editor["foundation_base_stone_cost"]),
        foundation_base_max_spirit=int(editor["foundation_base_max_spirit"]),
        resource_level_multiplier=float(editor["resource_level_multiplier"]),
        resource_realm_multiplier=float(editor["resource_realm_multiplier"]),
        stat_level_multiplier=float(editor["stat_level_multiplier"]),
        stat_realm_multiplier=float(editor["stat_realm_multiplier"]),
    )


def get_recipes_payload() -> dict[str, Any]:
    recipes_data = load_json(RECIPES_PATH)
    return {"config": recipes_data, "rows": _get_high_tier_recipe_rows(recipes_data)}


def save_recipes_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recipes_data = load_json(RECIPES_PATH)
    updated = _build_draft_recipes(recipes_data, rows)
    save_json(RECIPES_PATH, updated)
    return get_recipes_payload()


def apply_recipe_ladder(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _apply_breakthrough_recipe_ladder_rules(
        payload["rows"],
        foundation_success=int(payload["foundation_success"]),
        foundation_time=int(payload["foundation_time"]),
        foundation_spirit=int(payload["foundation_spirit"]),
        golden_success=int(payload["golden_success"]),
        golden_time=int(payload["golden_time"]),
        golden_spirit=int(payload["golden_spirit"]),
        success_step=int(payload["success_step"]),
        time_step=int(payload["time_step"]),
        spirit_step=int(payload["spirit_step"]),
        lower_pill_count=int(payload["lower_pill_count"]),
        mat_herb_count=int(payload["mat_herb_count"]),
        foundation_herb_count=int(payload["foundation_herb_count"]),
    )


def get_enemies_payload() -> dict[str, Any]:
    enemies_data = load_json(ENEMIES_PATH)
    return {"config": enemies_data, "rows": _get_enemy_rows(enemies_data)}


def save_enemies_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    enemies_data = load_json(ENEMIES_PATH)
    updated = _build_draft_enemies(enemies_data, rows)
    save_json(ENEMIES_PATH, updated)
    return get_enemies_payload()


def get_areas_payload() -> dict[str, Any]:
    areas_data = load_json(AREAS_PATH)
    enemies_data = load_json(ENEMIES_PATH)
    items_data = load_json(ITEMS_PATH)
    recipes_data = load_json(RECIPES_PATH)
    item_name_map = _build_item_name_map(items_data, recipes_data)
    enemy_name_map = _build_enemy_name_map(enemies_data)
    overview_rows = _get_normal_area_editor_rows(areas_data, item_name_map)
    return {
        "config": areas_data,
        "overviewRows": overview_rows,
        "areaOptions": _get_normal_area_options(areas_data),
        "itemNameMap": item_name_map,
        "enemyNameMap": enemy_name_map,
    }


def save_areas_payload(config: dict[str, Any]) -> dict[str, Any]:
    save_json(AREAS_PATH, config)
    return get_areas_payload()


def get_spells_payload() -> dict[str, Any]:
    spells_data = load_json(SPELLS_PATH)
    options = [
        {"spellId": spell_id, "name": spell_cfg.get("name", spell_id), "type": spell_cfg.get("type", "")}
        for spell_id, spell_cfg in spells_data.get("spells", {}).items()
    ]
    return {"config": spells_data, "options": options}


def save_spells_payload(config: dict[str, Any]) -> dict[str, Any]:
    save_json(SPELLS_PATH, config)
    return get_spells_payload()


def apply_spell_batch(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _apply_spell_batch_rules(
        payload["rows"],
        level2_to_4_spirit_multiplier=float(payload["level2_to_4_spirit_multiplier"]) if payload.get("level2_to_4_spirit_multiplier") is not None else None,
        level5_plus_spirit_multiplier=float(payload["level5_plus_spirit_multiplier"]) if payload.get("level5_plus_spirit_multiplier") is not None else None,
        level1_to_4_use_multiplier=float(payload["level1_to_4_use_multiplier"]) if payload.get("level1_to_4_use_multiplier") is not None else None,
        level5_plus_use_multiplier=float(payload["level5_plus_use_multiplier"]) if payload.get("level5_plus_use_multiplier") is not None else None,
    )


def sync_local_data_from_server() -> dict[str, str]:
    sync_from_server()
    return {"message": "已从服务端同步最新 data 文件"}


def build_cultivation_preview(payload: dict[str, Any]) -> dict[str, Any]:
    base = load_all_configs()
    base_realms = base["realms"]
    base_recipes = base["recipes"]
    base_areas = base["areas"]
    base_enemies = base["enemies"]

    draft_realms = build_realms_draft(base_realms, payload["realmsEditor"])
    draft_recipes = _build_draft_recipes(base_recipes, payload["recipeRows"])
    draft_areas = payload["areasConfig"]
    draft_enemies = _build_draft_enemies(base_enemies, payload["enemyRows"])

    base_stone_gain_map = _build_level_max_spirit_stone_gain_map(base_realms, base_areas, base_enemies)
    draft_stone_gain_map = _build_level_max_spirit_stone_gain_map(draft_realms, draft_areas, draft_enemies)
    base_foundation_herb_per_day = _calc_foundation_herb_per_day(base_areas)
    draft_foundation_herb_per_day = _calc_foundation_herb_per_day(draft_areas)

    base_rows = build_time_rows_with_stone_gain(base_realms, base_recipes, base_stone_gain_map, base_foundation_herb_per_day)
    draft_rows = build_time_rows_with_stone_gain(draft_realms, draft_recipes, draft_stone_gain_map, draft_foundation_herb_per_day)

    return {
        "metrics": {
            "base_foundation_herb_per_day": base_foundation_herb_per_day,
            "draft_foundation_herb_per_day": draft_foundation_herb_per_day,
            "base_total_spirit_days": base_rows[-1]["cumulative_spirit_days"] if base_rows else 0,
            "draft_total_spirit_days": draft_rows[-1]["cumulative_spirit_days"] if draft_rows else 0,
            "base_total_material_days": base_rows[-1]["cumulative_material_days"] if base_rows else 0,
            "draft_total_material_days": draft_rows[-1]["cumulative_material_days"] if draft_rows else 0,
        },
        "realmSummary": {
            "base": _build_realm_summary_rows(base_rows, base_realms["realm_order"]),
            "draft": _build_realm_summary_rows(draft_rows, draft_realms["realm_order"]),
        },
        "upgradeDetail": {
            "base": _build_upgrade_detail_rows(base_rows),
            "draft": _build_upgrade_detail_rows(draft_rows),
        },
    }


def build_battle_preview(payload: dict[str, Any]) -> dict[str, Any]:
    base = load_all_configs()
    base_realms = base["realms"]
    base_areas = base["areas"]
    base_enemies = base["enemies"]

    draft_realms = build_realms_draft(base_realms, payload["realmsEditor"])
    draft_areas = payload["areasConfig"]
    draft_enemies = _build_draft_enemies(base_enemies, payload["enemyRows"])

    k_value = float(payload.get("k_value", DEFAULT_K_VALUE))
    skill_coef = float(payload.get("skill_coef", 1.0))
    battle_interval_seconds = float(payload.get("battle_interval_seconds", DEFAULT_BATTLE_INTERVAL_SECONDS))
    realm_name = str(payload.get("realm_name", base_realms.get("realm_order", ["炼气期"])[0]))
    level = int(payload.get("level", 1))
    area_id = str(payload.get("area_id", next(iter(draft_areas.get("normal_areas", {}).keys()), "")))

    base_cave = _check_foundation_cave_min_pass(base_realms, base_areas, base_enemies, k_value, skill_coef, battle_interval_seconds)
    draft_cave = _check_foundation_cave_min_pass(draft_realms, draft_areas, draft_enemies, k_value, skill_coef, battle_interval_seconds)
    base_tower = _build_tower_stage_max_floor_rows(base_realms, base_areas, base_enemies, k_value, skill_coef, battle_interval_seconds)
    draft_tower = _build_tower_stage_max_floor_rows(draft_realms, draft_areas, draft_enemies, k_value, skill_coef, battle_interval_seconds)

    base_player_attrs = build_player_attrs_from_realm(base_realms, realm_name, level)
    draft_player_attrs = build_player_attrs_from_realm(draft_realms, realm_name, level)
    base_area_cfg = base_areas.get("normal_areas", {}).get(area_id, {})
    draft_area_cfg = draft_areas.get("normal_areas", {}).get(area_id, {})
    base_custom = simulate_average(
        player_attrs=base_player_attrs,
        area_cfg=base_area_cfg,
        enemies_data=base_enemies,
        k_value=k_value,
        skill_coef=skill_coef,
        penetration=0.0,
        trials=DEFAULT_TRIALS,
        max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
        battle_interval_seconds=battle_interval_seconds,
        seed=FIXED_BATTLE_RANDOM_SEED,
    )
    draft_custom = simulate_average(
        player_attrs=draft_player_attrs,
        area_cfg=draft_area_cfg,
        enemies_data=draft_enemies,
        k_value=k_value,
        skill_coef=skill_coef,
        penetration=0.0,
        trials=DEFAULT_TRIALS,
        max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
        battle_interval_seconds=battle_interval_seconds,
        seed=FIXED_BATTLE_RANDOM_SEED,
    )

    base_matrix = build_checkpoint_matrix(
        realms_data=base_realms,
        areas_data=base_areas,
        enemies_data=base_enemies,
        k_value=k_value,
        skill_coef=skill_coef,
        checkpoints=(1, 5),
        trials=DEFAULT_TRIALS,
        max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
        battle_interval_seconds=battle_interval_seconds,
        penetration=0.0,
        seed=FIXED_BATTLE_RANDOM_SEED,
        target_realms=("炼气期", "筑基期", "金丹期"),
    )
    draft_matrix = build_checkpoint_matrix(
        realms_data=draft_realms,
        areas_data=draft_areas,
        enemies_data=draft_enemies,
        k_value=k_value,
        skill_coef=skill_coef,
        checkpoints=(1, 5),
        trials=DEFAULT_TRIALS,
        max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
        battle_interval_seconds=battle_interval_seconds,
        penetration=0.0,
        seed=FIXED_BATTLE_RANDOM_SEED,
        target_realms=("炼气期", "筑基期", "金丹期"),
    )

    return {
        "cave": {"base": base_cave, "draft": draft_cave},
        "tower": {"base": base_tower, "draft": draft_tower},
        "custom": {"base": _serialize_custom_battle(base_custom), "draft": _serialize_custom_battle(draft_custom)},
        "matrix": {
            "base": base_matrix["summary_rows"],
            "draft": draft_matrix["summary_rows"],
            "baseRewards": base_matrix["reward_rows"],
            "draftRewards": draft_matrix["reward_rows"],
        },
    }


def _serialize_custom_battle(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "avg_fights": result.get("avg_fights", 0.0),
        "avg_fights_per_hour": result.get("avg_fights_per_hour", 0.0),
        "avg_item_per_hour": result.get("avg_item_per_hour", {}),
        "infinite_fights": bool(result.get("infinite_fights", False)),
    }


def _safe_ratio(numerator: float, denominator: float, default: float) -> float:
    if denominator == 0:
        return default
    value = numerator / denominator
    if value <= 0:
        return default
    return float(f"{value:.2f}")


def _derive_default_params(realms_data: dict) -> dict[str, Any]:
    zhuji_levels = realms_data["realms"]["筑基期"]["levels"]
    jindan_levels = realms_data["realms"]["金丹期"]["levels"]
    z1_health = float(zhuji_levels["1"]["health"])
    z2_health = float(zhuji_levels["2"]["health"])
    j1_health = float(jindan_levels["1"]["health"])
    z1_attack = float(zhuji_levels["1"]["attack"])
    z2_attack = float(zhuji_levels["2"]["attack"])
    j1_attack = float(jindan_levels["1"]["attack"])
    z1_defense = float(zhuji_levels["1"]["defense"])
    z2_defense = float(zhuji_levels["2"]["defense"])
    j1_defense = float(jindan_levels["1"]["defense"])
    z1_cost = float(zhuji_levels["1"]["spirit_energy_cost"])
    z1_stone_cost = float(zhuji_levels["1"].get("spirit_stone_cost", 0))
    z2_cost = float(zhuji_levels["2"]["spirit_energy_cost"])
    j1_cost = float(jindan_levels["1"]["spirit_energy_cost"])
    z1_max = float(zhuji_levels["1"]["max_spirit_energy"])
    z2_max = float(zhuji_levels["2"]["max_spirit_energy"])
    j1_max = float(jindan_levels["1"]["max_spirit_energy"])
    resource_level_multiplier = _safe_ratio(z2_cost, z1_cost, 1.10)
    if resource_level_multiplier <= 1.0:
        resource_level_multiplier = _safe_ratio(z2_max, z1_max, 1.10)
    resource_realm_multiplier = _safe_ratio(j1_cost, z1_cost, 5.00)
    if resource_realm_multiplier <= 1.0:
        resource_realm_multiplier = _safe_ratio(j1_max, z1_max, 5.00)
    stat_level_multiplier = _safe_ratio(z2_health, z1_health, 1.10)
    if stat_level_multiplier <= 1.0:
        stat_level_multiplier = _safe_ratio(z2_attack, z1_attack, 1.10)
    stat_realm_multiplier = _safe_ratio(j1_health, z1_health, 5.00)
    if stat_realm_multiplier <= 1.0:
        stat_realm_multiplier = _safe_ratio(j1_attack, z1_attack, 5.00)
    return {
        "foundation_base_health": int(z1_health),
        "foundation_base_attack": int(z1_attack),
        "foundation_base_defense": int(z1_defense),
        "foundation_base_cost": int(z1_cost),
        "foundation_base_stone_cost": int(z1_stone_cost),
        "foundation_base_max_spirit": int(z1_max),
        "resource_level_multiplier": float(resource_level_multiplier),
        "resource_realm_multiplier": float(resource_realm_multiplier),
        "stat_level_multiplier": float(stat_level_multiplier),
        "stat_realm_multiplier": float(stat_realm_multiplier),
    }


def _get_lianqi_editor_rows(realms_data: dict) -> list[dict[str, Any]]:
    levels = realms_data["realms"]["炼气期"]["levels"]
    rows = []
    for level_str, cfg in sorted(levels.items(), key=lambda item: int(item[0])):
        rows.append(
            {
                "层级": int(level_str),
                "health": int(cfg.get("health", 0)),
                "attack": int(cfg.get("attack", 0)),
                "defense": int(cfg.get("defense", 0)),
                "spirit_stone_cost": int(cfg.get("spirit_stone_cost", 0)),
                "spirit_energy_cost": int(cfg.get("spirit_energy_cost", 0)),
                "max_spirit_energy": int(cfg.get("max_spirit_energy", 0)),
            }
        )
    return rows


def _get_high_tier_recipe_rows(recipes_data: dict) -> list[dict[str, Any]]:
    recipes = recipes_data.get("recipes", {})
    rows = []
    for recipe_id, lower_id in BREAKTHROUGH_RECIPE_CHAIN:
        recipe = recipes.get(recipe_id, {})
        materials = recipe.get("materials", {})
        rows.append(
            {
                "recipe_id": recipe_id,
                "丹药名称": str(recipe.get("name", recipe_id)),
                "lower_pill_id": lower_id,
                "成功率(%)": int(recipe.get("success_value", 0)),
                "耗时(秒)": int(float(recipe.get("base_time", 0))),
                "消耗灵气": int(recipe.get("spirit_energy", 0)),
                "低阶丹药数量": int(materials.get(lower_id, 0)) if lower_id else 0,
                "草药数量": int(materials.get("mat_herb", 0)),
                "破境草数量": int(materials.get("foundation_herb", 0)),
            }
        )
    return rows


def _build_draft_recipes(base_recipes: dict, rows: list[dict[str, Any]]) -> dict:
    draft = deepcopy(base_recipes)
    recipes = draft.get("recipes", {})
    for row in rows:
        recipe_id = str(row["recipe_id"])
        lower_id = str(row.get("lower_pill_id", ""))
        recipe = recipes.get(recipe_id)
        if not recipe:
            continue
        recipe["success_value"] = max(0, min(100, int(row["成功率(%)"])))
        recipe["base_time"] = float(max(1, int(row["耗时(秒)"])))
        recipe["spirit_energy"] = max(0, int(row["消耗灵气"]))
        next_materials: dict[str, int] = {}
        if lower_id:
            next_materials[lower_id] = max(1, int(row["低阶丹药数量"]))
        mat_herb = max(0, int(row["草药数量"]))
        foundation_herb = max(0, int(row["破境草数量"]))
        if mat_herb > 0:
            next_materials["mat_herb"] = mat_herb
        if foundation_herb > 0:
            next_materials["foundation_herb"] = foundation_herb
        recipe["materials"] = next_materials
    return draft


def _apply_breakthrough_recipe_ladder_rules(rows: list[dict[str, Any]], **kwargs: int) -> list[dict[str, Any]]:
    row_map = {str(row.get("recipe_id", "")): dict(row) for row in rows}
    updated: list[dict[str, Any]] = []
    for index, (recipe_id, lower_id) in enumerate(BREAKTHROUGH_RECIPE_CHAIN):
        row = row_map.get(recipe_id, {"recipe_id": recipe_id, "丹药名称": recipe_id, "lower_pill_id": lower_id})
        row["recipe_id"] = recipe_id
        row["lower_pill_id"] = lower_id
        if recipe_id == "foundation_pill":
            row["成功率(%)"] = max(0, min(100, int(kwargs["foundation_success"])))
            row["耗时(秒)"] = max(1, int(kwargs["foundation_time"]))
            row["消耗灵气"] = max(0, int(kwargs["foundation_spirit"]))
            row["低阶丹药数量"] = 0
            row["草药数量"] = max(1, int(kwargs["mat_herb_count"]))
            row["破境草数量"] = max(1, int(kwargs["foundation_herb_count"]))
        elif recipe_id == "golden_core_pill":
            row["成功率(%)"] = max(0, min(100, int(kwargs["golden_success"])))
            row["耗时(秒)"] = max(1, int(kwargs["golden_time"]))
            row["消耗灵气"] = max(0, int(kwargs["golden_spirit"]))
            row["低阶丹药数量"] = max(1, int(kwargs["lower_pill_count"]))
            row["草药数量"] = max(1, int(kwargs["mat_herb_count"]))
            row["破境草数量"] = 0
        else:
            tier_step = index - 1
            row["成功率(%)"] = max(0, min(100, int(kwargs["golden_success"] - kwargs["success_step"] * tier_step)))
            row["耗时(秒)"] = max(1, int(kwargs["golden_time"] + kwargs["time_step"] * tier_step))
            row["消耗灵气"] = max(0, int(kwargs["golden_spirit"] + kwargs["spirit_step"] * tier_step))
            row["低阶丹药数量"] = max(1, int(kwargs["lower_pill_count"]))
            row["草药数量"] = max(1, int(kwargs["mat_herb_count"]))
            row["破境草数量"] = 0
        updated.append(row)
    return updated


def _get_enemy_rows(enemies_data: dict) -> list[dict[str, Any]]:
    rows = []
    for template_id, cfg in enemies_data.get("templates", {}).items():
        growth = cfg.get("growth", {})
        rows.append(
            {
                "template_id": str(template_id),
                "敌人名称": str(cfg.get("name", template_id)),
                "health_base": int(growth.get("health_base", 0)),
                "attack_base": int(growth.get("attack_base", 0)),
                "defense_base": int(growth.get("defense_base", 0)),
                "health_growth": float(growth.get("health_growth", 1.0)),
                "attack_growth": float(growth.get("attack_growth", 1.0)),
                "defense_growth": float(growth.get("defense_growth", 1.0)),
            }
        )
    return rows


def _build_draft_enemies(base_enemies: dict, rows: list[dict[str, Any]]) -> dict:
    draft = deepcopy(base_enemies)
    templates = draft.get("templates", {})
    for row in rows:
        template_id = str(row["template_id"])
        if template_id not in templates:
            continue
        growth = templates[template_id].setdefault("growth", {})
        growth["health_base"] = int(row["health_base"])
        growth["attack_base"] = int(row["attack_base"])
        growth["defense_base"] = int(row["defense_base"])
        growth["health_growth"] = float(row["health_growth"])
        growth["attack_growth"] = float(row["attack_growth"])
        growth["defense_growth"] = float(row["defense_growth"])
    return draft


def _build_item_name_map(items_data: dict, recipes_data: dict) -> dict[str, str]:
    item_name_map = {str(item_id): str(cfg.get("name", item_id)) for item_id, cfg in items_data.get("items", {}).items()}
    for recipe_id, cfg in recipes_data.get("recipes", {}).items():
        item_name_map.setdefault(str(recipe_id), str(cfg.get("name", recipe_id)))
        product = str(cfg.get("product", ""))
        if product:
            item_name_map.setdefault(product, str(cfg.get("name", product)))
    return item_name_map


def _build_enemy_name_map(enemies_data: dict) -> dict[str, str]:
    return {str(template_id): str(cfg.get("name", template_id)) for template_id, cfg in enemies_data.get("templates", {}).items()}


def _get_normal_area_options(areas_data: dict) -> list[dict[str, str]]:
    return [{"id": str(area_id), "name": str(area_cfg.get("name", area_id))} for area_id, area_cfg in areas_data.get("normal_areas", {}).items()]


def _calc_area_spirit_stone_expected_per_fight(area_cfg: dict) -> float:
    templates = area_cfg.get("enemies_template", [])
    if not templates:
        return 0.0
    weights = [float(max(0, t.get("weight", 0))) for t in templates]
    weight_sum = sum(weights)
    probs = [1.0 if i == 0 else 0.0 for i in range(len(templates))] if weight_sum <= 0 else [w / weight_sum for w in weights]
    expected = 0.0
    for idx, template_cfg in enumerate(templates):
        drop_info = template_cfg.get("drops", {}).get("spirit_stone")
        if not drop_info:
            continue
        chance = float(drop_info.get("chance", 1.0))
        min_amount = int(drop_info.get("min", 0))
        max_amount = int(drop_info.get("max", min_amount))
        expected += probs[idx] * chance * ((float(min_amount) + float(max_amount)) / 2.0)
    return expected


def _get_normal_area_editor_rows(areas_data: dict, item_name_map: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for area_id, area_cfg in areas_data.get("normal_areas", {}).items():
        templates = area_cfg.get("enemies_template", [])
        min_levels = []
        max_levels = []
        drop_items = set()
        total_weight = 0
        for template_cfg in templates:
            enemy_desc = (template_cfg.get("enemies") or [{}])[0]
            min_levels.append(int(enemy_desc.get("min_level", 1)))
            max_levels.append(int(enemy_desc.get("max_level", 1)))
            total_weight += int(template_cfg.get("weight", 0))
            for item_id in template_cfg.get("drops", {}).keys():
                drop_items.add(item_name_map.get(str(item_id), str(item_id)))
        level_range = f"{min(min_levels)}-{max(max_levels)}" if min_levels and max_levels else "-"
        drop_kind = "，".join(sorted(drop_items)) if drop_items else "-"
        expected_per_hour = _calc_area_spirit_stone_expected_per_fight(area_cfg) * (3600.0 / 5.0)
        rows.append(
            {
                "area_id": str(area_id),
                "区域名称": str(area_cfg.get("name", area_id)),
                "默认连续历练": bool(area_cfg.get("default_continuous", False)),
                "敌人池数量": len(templates),
                "权重总和": total_weight,
                "敌人等级范围": level_range,
                "掉落种类": drop_kind,
                "理论最大灵石掉落效率（每小时）": format_number(expected_per_hour),
            }
        )
    return rows


def _apply_spell_batch_rules(
    rows: list[dict[str, Any]],
    *,
    level2_to_4_spirit_multiplier: float | None,
    level5_plus_spirit_multiplier: float | None,
    level1_to_4_use_multiplier: float | None,
    level5_plus_use_multiplier: float | None,
) -> list[dict[str, Any]]:
    row_map = {int(row["level"]): dict(row) for row in rows}
    if 1 not in row_map:
        return rows
    updated = []
    base_level1_spirit = max(0, int(row_map[1]["spirit_cost"]))
    base_level1_use = max(0, int(row_map[1]["use_count_required"]))
    prev_spirit = base_level1_spirit
    prev_use = base_level1_use
    for level in sorted(row_map.keys()):
        row = dict(row_map[level])
        if level == 1:
            updated.append(row)
            continue
        if level == 2:
            if level2_to_4_spirit_multiplier is not None:
                row["spirit_cost"] = max(0, int(round(base_level1_spirit * level2_to_4_spirit_multiplier)))
            if level1_to_4_use_multiplier is not None:
                row["use_count_required"] = max(0, int(round(base_level1_use * level1_to_4_use_multiplier)))
        else:
            if level <= 4:
                if level2_to_4_spirit_multiplier is not None:
                    row["spirit_cost"] = max(0, int(round(prev_spirit * level2_to_4_spirit_multiplier)))
            elif level5_plus_spirit_multiplier is not None:
                row["spirit_cost"] = max(0, int(round(prev_spirit * level5_plus_spirit_multiplier)))
            if level <= 4:
                if level1_to_4_use_multiplier is not None:
                    row["use_count_required"] = max(0, int(round(prev_use * level1_to_4_use_multiplier)))
            elif level5_plus_use_multiplier is not None:
                row["use_count_required"] = max(0, int(round(prev_use * level5_plus_use_multiplier)))
        prev_spirit = int(row["spirit_cost"])
        prev_use = int(row["use_count_required"])
        updated.append(row)
    return updated


def _calc_foundation_herb_per_day(areas_data: dict) -> float:
    daily_areas = areas_data.get("daily_areas", {})
    cave = daily_areas.get("foundation_herb_cave", {})
    templates = cave.get("enemies_template", [])
    if not templates:
        return 30.0
    expected = 0.0
    total_weight = sum(float(t.get("weight", 0)) for t in templates)
    for template in templates:
        prob = (float(template.get("weight", 0)) / total_weight) if total_weight > 0 else 0.0
        drop = template.get("drops", {}).get("foundation_herb")
        if not drop:
            continue
        chance = float(drop.get("chance", 1.0))
        min_amount = int(drop.get("min", 0))
        max_amount = int(drop.get("max", min_amount))
        expected += prob * chance * ((min_amount + max_amount) / 2.0)
    return expected * 30.0 if expected > 0 else 30.0


def _build_level_max_spirit_stone_gain_map(realms_data: dict, areas_data: dict, enemies_data: dict) -> dict[str, float]:
    matrix = build_checkpoint_matrix(
        realms_data=realms_data,
        areas_data=areas_data,
        enemies_data=enemies_data,
        k_value=DEFAULT_K_VALUE,
        skill_coef=1.0,
        checkpoints=(1, 5, 10),
        trials=DEFAULT_TRIALS,
        max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
        battle_interval_seconds=5.0,
        penetration=0.0,
        seed=FIXED_BATTLE_RANDOM_SEED,
    )
    reward_by_key: dict[tuple[str, int, str], float] = {}
    for reward_row in matrix["reward_rows"]:
        if str(reward_row.get("item_id")) != "spirit_stone":
            continue
        reward_by_key[(str(reward_row["realm_name"]), int(reward_row["level"]), str(reward_row["area_id"]))] = float(reward_row.get("avg_per_hour", 0.0))
    best_by_stage: dict[str, float] = {}
    for row in matrix["summary_rows"]:
        key = f"{row['realm_name']}:{int(row['level'])}"
        stage_reward = reward_by_key.get((str(row["realm_name"]), int(row["level"]), str(row["area_id"])), 0.0)
        best_by_stage[key] = max(best_by_stage.get(key, 0.0), stage_reward)

    for realm_name in realms_data.get("realm_order", []):
        realm_cfg = realms_data.get("realms", {}).get(realm_name, {})
        max_level = int(realm_cfg.get("max_level", 0))
        for level in range(1, max_level + 1):
            if f"{realm_name}:{level}" in best_by_stage:
                continue
            nearest = None
            for candidate in (10, 5, 1):
                if candidate <= max_level and f"{realm_name}:{candidate}" in best_by_stage:
                    nearest = best_by_stage[f"{realm_name}:{candidate}"]
                    break
            if nearest is not None:
                best_by_stage[f"{realm_name}:{level}"] = nearest
    return best_by_stage


def _build_realm_summary_rows(rows: list[dict[str, Any]], realm_order: list[str]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        realm_name = str(row["realm_name"])
        current = grouped.setdefault(realm_name, {"realm_spirit_days": 0.0, "realm_stone_days": 0.0, "realm_material_days": 0.0})
        current["realm_spirit_days"] += float(row["step_spirit_hours"]) / 24.0
        current["realm_stone_days"] += float(row["step_stone_hours"]) / 24.0
        current["realm_material_days"] += float(row["step_material_hours"]) / 24.0
    result = []
    for realm_name in realm_order:
        current = grouped.get(realm_name)
        if not current:
            continue
        gather = current["realm_spirit_days"] + current["realm_stone_days"]
        max_days = max(gather, current["realm_material_days"])
        result.append(
            {
                "大境界": realm_name,
                "该境界灵气总耗时": _format_duration(current["realm_spirit_days"], source_unit="days"),
                "该境界灵石总耗时": _format_duration(current["realm_stone_days"], source_unit="days"),
                "该境界材料总耗时": _format_duration(current["realm_material_days"], source_unit="days"),
                "该境界Max耗时": _format_duration(max_days, source_unit="days"),
            }
        )
    return result


def _build_upgrade_detail_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "序号": int(row["step_index"]),
            "从": str(row["from_stage"]),
            "灵石消耗": int(row["spirit_stone_cost"]),
            "灵气消耗": int(row["spirit_energy_cost"]),
            "破境草需求": "" if int(row["foundation_herb_needed"]) == 0 else int(row["foundation_herb_needed"]),
            "层间灵气耗时": _format_duration(float(row["step_spirit_hours"]), source_unit="hours"),
            "层间灵石耗时": _format_duration(float(row["step_stone_hours"]), source_unit="hours"),
            "层间材料耗时": _format_duration(float(row["step_material_hours"]), source_unit="hours"),
            "累计灵气耗时": _format_duration(float(row["cumulative_spirit_days"]), source_unit="days"),
            "累计灵石耗时": _format_duration(float(row["cumulative_stone_days"]), source_unit="days"),
            "累计材料耗时": _format_duration(float(row["cumulative_material_days"]), source_unit="days"),
        }
        for row in rows
    ]


def _format_duration(value: float, *, source_unit: str) -> str:
    total_hours = float(value) if source_unit == "hours" else float(value) * 24.0
    if total_hours <= 0.0:
        return ""
    if total_hours < 1.0:
        minutes_text = format_number(total_hours * 60.0)
        return "" if minutes_text == "0" else f"{minutes_text} 分钟"
    if total_hours < 24.0:
        hours_text = format_number(total_hours)
        return "" if hours_text == "0" else f"{hours_text} 小时"
    days_text = format_number(total_hours / 24.0)
    return "" if days_text == "0" else f"{days_text} 天"


def _check_foundation_cave_min_pass(
    realms_data: dict,
    areas_data: dict,
    enemies_data: dict,
    k_value: float,
    skill_coef: float,
    battle_interval_seconds: float,
) -> dict[str, Any]:
    cave = areas_data.get("daily_areas", {}).get("foundation_herb_cave")
    if not cave:
        return {"exists": False}
    lianqi = realms_data.get("realms", {}).get("炼气期", {})
    max_level = int(lianqi.get("max_level", 0))
    lianqi_max_stage = f"炼气期第{max_level}层" if max_level > 0 else "炼气期"
    can_lianqi_max = False
    for level in range(1, max_level + 1):
        attrs = build_player_attrs_from_realm(realms_data, "炼气期", level)
        result = simulate_average(
            player_attrs=attrs,
            area_cfg=cave,
            enemies_data=enemies_data,
            k_value=k_value,
            skill_coef=skill_coef,
            penetration=0.0,
            trials=DEFAULT_TRIALS,
            max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
            battle_interval_seconds=battle_interval_seconds,
            seed=FIXED_BATTLE_RANDOM_SEED,
        )
        if float(result.get("avg_fights", 0)) >= 1 or bool(result.get("infinite_fights", False)):
            can_lianqi_max = True
            return {"exists": True, "can_lianqi_max": True, "lianqi_max_stage": lianqi_max_stage, "min_pass_stage": f"炼气期第{level}层"}
    return {"exists": True, "can_lianqi_max": can_lianqi_max, "lianqi_max_stage": lianqi_max_stage, "min_pass_stage": ""}


def _build_tower_stage_max_floor_rows(realms_data: dict, areas_data: dict, enemies_data: dict, k_value: float, skill_coef: float, battle_interval_seconds: float) -> list[dict[str, Any]]:
    return build_tower_max_floor_by_stage(
        realms_data=realms_data,
        areas_data=areas_data,
        enemies_data=enemies_data,
        k_value=k_value,
        skill_coef=skill_coef,
        battle_interval_seconds=battle_interval_seconds,
    )
