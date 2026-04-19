from copy import deepcopy
import html
import json

import pandas as pd
import streamlit as st

from src.io.data_paths import REALMS_PATH, RECIPES_PATH, AREAS_PATH, ENEMIES_PATH, ITEMS_PATH
from src.io.data_sync import ensure_local_data
from src.io.json_store import load_json, save_json
from src.io.realms_text_updater import save_realms_numeric_fields_preserve_format
from src.model.battle_model import (
    DEFAULT_BATTLE_INTERVAL_SECONDS,
    DEFAULT_K_VALUE,
    DEFAULT_MAX_FIGHTS_PER_TRIAL,
    DEFAULT_TRIALS,
    FIXED_BATTLE_RANDOM_SEED,
    build_tower_max_floor_by_stage,
    build_checkpoint_matrix,
    build_player_attrs_from_realm,
    simulate_average,
    simulate_trial,
)
from src.model.formatting import format_number
from src.model.realm_generator import apply_generation_rules
from src.model.time_model import build_time_rows_with_stone_gain


st.set_page_config(page_title="境界数值模型", layout="wide")
st.title("境界数值模型（一期）")
st.caption("目标：评估玩家从炼气一层到最高层的修炼耗时合理性。")


def _load_data():
    ensure_local_data()
    return (
        load_json(REALMS_PATH),
        load_json(RECIPES_PATH),
        load_json(AREAS_PATH),
        load_json(ENEMIES_PATH),
        load_json(ITEMS_PATH),
    )


HIGH_TIER_CHAIN = [
    ("golden_core_pill", "foundation_pill"),
    ("nascent_soul_pill", "golden_core_pill"),
    ("spirit_separation_pill", "nascent_soul_pill"),
    ("void_refining_pill", "spirit_separation_pill"),
    ("body_integration_pill", "void_refining_pill"),
    ("mahayana_pill", "body_integration_pill"),
    ("tribulation_pill", "mahayana_pill"),
]

def _safe_ratio(numerator: float, denominator: float, default: float) -> float:
    if denominator == 0:
        return default
    value = numerator / denominator
    if value <= 0:
        return default
    return float(f"{value:.2f}")


def _derive_default_params(realms_data: dict) -> dict:
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
    z1_stone_cost = float(zhuji_levels["1"]["spirit_stone_cost"])
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
    if stat_level_multiplier <= 1.0:
        stat_level_multiplier = _safe_ratio(z2_defense, z1_defense, 1.10)

    stat_realm_multiplier = _safe_ratio(j1_health, z1_health, 5.00)
    if stat_realm_multiplier <= 1.0:
        stat_realm_multiplier = _safe_ratio(j1_attack, z1_attack, 5.00)
    if stat_realm_multiplier <= 1.0:
        stat_realm_multiplier = _safe_ratio(j1_defense, z1_defense, 5.00)

    return {
        "foundation_base_health": int(z1_health),
        "foundation_base_attack": int(z1_attack),
        "foundation_base_defense": int(z1_defense),
        "foundation_base_cost": int(z1_cost),
        "foundation_base_stone_cost": int(z1_stone_cost),
        "foundation_base_max_spirit": int(z1_max),
        "resource_level_multiplier": float(f"{resource_level_multiplier:.2f}"),
        "resource_realm_multiplier": float(f"{resource_realm_multiplier:.2f}"),
        "stat_level_multiplier": float(f"{stat_level_multiplier:.2f}"),
        "stat_realm_multiplier": float(f"{stat_realm_multiplier:.2f}"),
    }


def _get_lianqi_editor_df(realms_data: dict) -> pd.DataFrame:
    lianqi_levels = realms_data["realms"]["炼气期"]["levels"]
    rows = []
    for level in sorted(lianqi_levels.keys(), key=int):
        info = lianqi_levels[level]
        rows.append(
            {
                "层级": int(level),
                "health": int(info.get("health", 0)),
                "attack": int(info.get("attack", 0)),
                "defense": int(info.get("defense", 0)),
                "spirit_stone_cost": int(info.get("spirit_stone_cost", 0)),
                "spirit_energy_cost": int(info["spirit_energy_cost"]),
                "max_spirit_energy": int(info["max_spirit_energy"]),
            }
        )
    return pd.DataFrame(rows)


def _extract_lianqi_values(df: pd.DataFrame):
    healths = {}
    attacks = {}
    defenses = {}
    stone_costs = {}
    costs = {}
    max_spirits = {}
    for _, row in df.iterrows():
        level = int(row["层级"])
        healths[level] = int(row["health"])
        attacks[level] = int(row["attack"])
        defenses[level] = int(row["defense"])
        stone_costs[level] = int(row["spirit_stone_cost"])
        costs[level] = int(row["spirit_energy_cost"])
        max_spirits[level] = int(row["max_spirit_energy"])
    return healths, attacks, defenses, stone_costs, costs, max_spirits


def _prepare_display_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in [
        "step_spirit_hours",
        "step_stone_hours",
        "step_material_hours",
        "cumulative_spirit_days",
        "cumulative_stone_days",
        "cumulative_material_days",
    ]:
        df[col + "_display"] = df[col].map(format_number)
    return df


def _init_realm_draft_state(realms_data: dict):
    signature = _realms_signature(realms_data)
    prev_signature = st.session_state.get("realm_source_signature", "")
    should_reset = prev_signature != signature

    defaults = _derive_default_params(realms_data)
    if "draft_foundation_base_health" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_health"] = defaults["foundation_base_health"]
    if "draft_foundation_base_attack" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_attack"] = defaults["foundation_base_attack"]
    if "draft_foundation_base_defense" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_defense"] = defaults["foundation_base_defense"]
    if "draft_foundation_base_cost" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_cost"] = defaults["foundation_base_cost"]
    if "draft_foundation_base_stone_cost" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_stone_cost"] = defaults["foundation_base_stone_cost"]
    if "draft_foundation_base_max_spirit" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_max_spirit"] = defaults["foundation_base_max_spirit"]
    if "draft_resource_level_multiplier" not in st.session_state or should_reset:
        st.session_state["draft_resource_level_multiplier"] = defaults["resource_level_multiplier"]
    if "draft_resource_realm_multiplier" not in st.session_state or should_reset:
        st.session_state["draft_resource_realm_multiplier"] = defaults["resource_realm_multiplier"]
    if "draft_stat_level_multiplier" not in st.session_state or should_reset:
        st.session_state["draft_stat_level_multiplier"] = defaults["stat_level_multiplier"]
    if "draft_stat_realm_multiplier" not in st.session_state or should_reset:
        st.session_state["draft_stat_realm_multiplier"] = defaults["stat_realm_multiplier"]
    if "draft_lianqi_rows" not in st.session_state or should_reset:
        st.session_state["draft_lianqi_rows"] = _get_lianqi_editor_df(realms_data).to_dict("records")
    # 兼容旧会话脏状态：若四个参数都回落到 1/1.00，则按配置重置。
    if (
        int(st.session_state.get("draft_foundation_base_health", 1)) == 1
        and int(st.session_state.get("draft_foundation_base_attack", 1)) == 1
        and int(st.session_state.get("draft_foundation_base_defense", 1)) == 1
        and int(st.session_state.get("draft_foundation_base_cost", 1)) == 1
        and int(st.session_state.get("draft_foundation_base_stone_cost", 1)) == 1
        and int(st.session_state.get("draft_foundation_base_max_spirit", 1)) == 1
        and float(st.session_state.get("draft_resource_level_multiplier", 1.0)) == 1.0
        and float(st.session_state.get("draft_resource_realm_multiplier", 1.0)) == 1.0
        and float(st.session_state.get("draft_stat_level_multiplier", 1.0)) == 1.0
        and float(st.session_state.get("draft_stat_realm_multiplier", 1.0)) == 1.0
    ):
        st.session_state["draft_foundation_base_health"] = defaults["foundation_base_health"]
        st.session_state["draft_foundation_base_attack"] = defaults["foundation_base_attack"]
        st.session_state["draft_foundation_base_defense"] = defaults["foundation_base_defense"]
        st.session_state["draft_foundation_base_cost"] = defaults["foundation_base_cost"]
        st.session_state["draft_foundation_base_stone_cost"] = defaults["foundation_base_stone_cost"]
        st.session_state["draft_foundation_base_max_spirit"] = defaults["foundation_base_max_spirit"]
        st.session_state["draft_resource_level_multiplier"] = defaults["resource_level_multiplier"]
        st.session_state["draft_resource_realm_multiplier"] = defaults["resource_realm_multiplier"]
        st.session_state["draft_stat_level_multiplier"] = defaults["stat_level_multiplier"]
        st.session_state["draft_stat_realm_multiplier"] = defaults["stat_realm_multiplier"]
    st.session_state["realm_source_signature"] = signature


def _get_high_tier_recipe_editor_df(recipes_data: dict) -> pd.DataFrame:
    recipes = recipes_data.get("recipes", {})
    rows = []
    for recipe_id, lower_id in HIGH_TIER_CHAIN:
        recipe = recipes.get(recipe_id, {})
        materials = recipe.get("materials", {})
        rows.append(
            {
                "recipe_id": recipe_id,
                "丹药名称": str(recipe.get("name", recipe_id)),
                "lower_pill_id": lower_id,
                "低阶丹药数量": int(materials.get(lower_id, 1)),
                "破境草数量": int(materials.get("foundation_herb", 1)),
            }
        )
    return pd.DataFrame(rows)


def _init_recipe_draft_state(recipes_data: dict):
    signature = _recipes_signature(recipes_data)
    prev_signature = st.session_state.get("recipe_source_signature", "")
    if "draft_high_tier_recipe_rows" not in st.session_state or prev_signature != signature:
        st.session_state["draft_high_tier_recipe_rows"] = _get_high_tier_recipe_editor_df(recipes_data).to_dict("records")
    st.session_state["recipe_source_signature"] = signature


def _get_enemy_template_editor_df(enemies_data: dict) -> pd.DataFrame:
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
    return pd.DataFrame(rows)


def _enemies_signature(enemies_data: dict) -> str:
    return json.dumps(enemies_data, ensure_ascii=False, sort_keys=True)


def _init_enemy_draft_state(enemies_data: dict):
    signature = _enemies_signature(enemies_data)
    prev_signature = st.session_state.get("enemy_source_signature", "")
    if "draft_enemy_template_rows" not in st.session_state or prev_signature != signature:
        st.session_state["draft_enemy_template_rows"] = _get_enemy_template_editor_df(enemies_data).to_dict("records")
    st.session_state["enemy_source_signature"] = signature


def _build_draft_enemies(base_enemies: dict, rows: list[dict]) -> dict:
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


def _areas_signature(areas_data: dict) -> str:
    return json.dumps(areas_data, ensure_ascii=False, sort_keys=True)


def _init_areas_draft_state(areas_data: dict):
    signature = _areas_signature(areas_data)
    prev_signature = st.session_state.get("areas_source_signature", "")
    if "draft_areas_data" not in st.session_state or prev_signature != signature:
        st.session_state["draft_areas_data"] = deepcopy(areas_data)

    normal_areas = st.session_state["draft_areas_data"].get("normal_areas", {})
    if normal_areas:
        first_area_id = next(iter(normal_areas.keys()))
        if st.session_state.get("draft_area_selected_area_id") not in normal_areas:
            st.session_state["draft_area_selected_area_id"] = first_area_id
            st.session_state["draft_area_selected_template_index"] = 0
    st.session_state["areas_source_signature"] = signature


def _build_draft_areas(base_areas: dict) -> dict:
    return deepcopy(st.session_state.get("draft_areas_data", base_areas))


def _build_enemy_name_map(enemies_data: dict) -> dict[str, str]:
    return {
        str(template_id): str(cfg.get("name", template_id))
        for template_id, cfg in enemies_data.get("templates", {}).items()
    }


def _format_drop_summary(drops: dict, item_name_map: dict[str, str]) -> str:
    if not drops:
        return "-"
    parts = []
    for item_id in sorted(drops.keys()):
        info = drops[item_id]
        item_name = item_name_map.get(str(item_id), str(item_id))
        min_amount = int(info.get("min", 0))
        max_amount = int(info.get("max", min_amount))
        chance = float(info.get("chance", 1.0))
        amount_text = f"{min_amount}" if min_amount == max_amount else f"{min_amount}-{max_amount}"
        parts.append(f"{item_name} {amount_text} ({format_number(chance * 100)}%)")
    return "，".join(parts)


def _calc_area_spirit_stone_expected_per_fight(area_cfg: dict) -> float:
    templates = area_cfg.get("enemies_template", [])
    if not templates:
        return 0.0
    weights = [float(max(0, t.get("weight", 0))) for t in templates]
    weight_sum = sum(weights)
    if weight_sum <= 0.0:
        probs = [1.0 if i == 0 else 0.0 for i in range(len(templates))]
    else:
        probs = [w / weight_sum for w in weights]
    expected = 0.0
    for idx, template_cfg in enumerate(templates):
        drop_info = template_cfg.get("drops", {}).get("spirit_stone")
        if not drop_info:
            continue
        chance = float(drop_info.get("chance", 1.0))
        min_amount = int(drop_info.get("min", 0))
        max_amount = int(drop_info.get("max", min_amount))
        if max_amount < min_amount:
            max_amount = min_amount
        expected_amount = (float(min_amount) + float(max_amount)) / 2.0
        expected += probs[idx] * chance * expected_amount
    return expected


def _format_spirit_efficiency_compare(base_area_cfg: dict, draft_area_cfg: dict) -> str:
    fights_per_hour = 3600.0 / 5.0
    base_value = _calc_area_spirit_stone_expected_per_fight(base_area_cfg) * fights_per_hour
    draft_value = _calc_area_spirit_stone_expected_per_fight(draft_area_cfg) * fights_per_hour
    base_text = format_number(base_value)
    draft_text = format_number(draft_value)
    if base_text == draft_text:
        return draft_text
    return f"{base_text}→{draft_text}"


def _get_normal_area_editor_df(areas_data: dict, item_name_map: dict[str, str], base_areas_data: dict | None = None) -> pd.DataFrame:
    rows = []
    for area_id, area_cfg in areas_data.get("normal_areas", {}).items():
        base_area_cfg = (base_areas_data or areas_data).get("normal_areas", {}).get(area_id, area_cfg)
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
        if min_levels and max_levels:
            level_range = f"{min(min_levels)}-{max(max_levels)}"
        else:
            level_range = "-"
        drop_summary = "，".join(sorted(drop_items)) if drop_items else "-"
        rows.append(
            {
                "area_id": str(area_id),
                "区域名称": str(area_cfg.get("name", area_id)),
                "默认连续历练": bool(area_cfg.get("default_continuous", False)),
                "敌人池数量": len(templates),
                "权重总和": total_weight,
                "敌人等级范围": level_range,
                "掉落种类": drop_summary,
                "理论最大灵石掉落效率（每小时）": _format_spirit_efficiency_compare(base_area_cfg, area_cfg),
            }
        )
    return pd.DataFrame(rows)


def _get_area_template_editor_df(area_cfg: dict, enemy_name_map: dict[str, str], item_name_map: dict[str, str]) -> pd.DataFrame:
    rows = []
    for idx, template_cfg in enumerate(area_cfg.get("enemies_template", []), start=1):
        enemy_desc = (template_cfg.get("enemies") or [{}])[0]
        template_id = str(enemy_desc.get("template", ""))
        min_level = int(enemy_desc.get("min_level", 1))
        max_level = int(enemy_desc.get("max_level", min_level))
        rows.append(
            {
                "序号": idx,
                "敌人模板": template_id,
                "敌人名称": enemy_name_map.get(template_id, template_id),
                "等级下限": min_level,
                "等级上限": max_level,
                "权重": int(template_cfg.get("weight", 0)),
                "掉落摘要": _format_drop_summary(template_cfg.get("drops", {}), item_name_map),
            }
        )
    return pd.DataFrame(rows)


def _get_area_drop_editor_df(area_cfg: dict, template_index: int, item_name_map: dict[str, str]) -> pd.DataFrame:
    templates = area_cfg.get("enemies_template", [])
    if template_index < 0 or template_index >= len(templates):
        return pd.DataFrame(columns=["删除", "item_id", "掉落名称", "min", "max", "chance"])
    rows = []
    for item_id, info in templates[template_index].get("drops", {}).items():
        min_amount = int(info.get("min", 0))
        max_amount = int(info.get("max", min_amount))
        rows.append(
            {
                "删除": False,
                "item_id": str(item_id),
                "掉落名称": item_name_map.get(str(item_id), str(item_id)),
                "min": min_amount,
                "max": max_amount,
                "chance": float(info.get("chance", 1.0)),
            }
        )
    return pd.DataFrame(rows)


def _format_reward_compare_text(
    before_items: dict[str, float],
    after_items: dict[str, float],
    item_name_map: dict[str, str],
) -> str:
    keys = sorted(set(before_items.keys()) | set(after_items.keys()))
    if not keys:
        return "-"
    parts = []
    for item_id in keys:
        name = item_name_map.get(item_id, item_id)
        before_v = float(before_items.get(item_id, 0.0))
        after_v = float(after_items.get(item_id, 0.0))
        parts.append(f"{name}: {_build_compare_html(format_number(before_v), format_number(after_v))}")
    return "，".join(parts)


def _realms_signature(realms_data: dict) -> str:
    return json.dumps(realms_data, ensure_ascii=False, sort_keys=True)


def _recipes_signature(recipes_data: dict) -> str:
    return json.dumps(recipes_data, ensure_ascii=False, sort_keys=True)


def _build_draft_recipes(base_recipes: dict, recipe_rows: list[dict]) -> dict:
    draft = deepcopy(base_recipes)
    recipes = draft.get("recipes", {})
    for row in recipe_rows:
        recipe_id = str(row["recipe_id"])
        lower_id = str(row["lower_pill_id"])
        lower_count = int(row["低阶丹药数量"])
        herb_count = int(row["破境草数量"])
        if recipe_id not in recipes:
            continue
        recipes[recipe_id]["materials"] = {
            "foundation_herb": herb_count,
            lower_id: lower_count,
        }
    return draft


def _build_draft_realms(base_realms: dict) -> dict:
    lianqi_df = pd.DataFrame(st.session_state["draft_lianqi_rows"])
    lianqi_healths, lianqi_attacks, lianqi_defenses, lianqi_stone_costs, lianqi_costs, lianqi_max_spirits = _extract_lianqi_values(lianqi_df)
    return apply_generation_rules(
        realms_data=deepcopy(base_realms),
        lianqi_healths=lianqi_healths,
        lianqi_attacks=lianqi_attacks,
        lianqi_defenses=lianqi_defenses,
        lianqi_costs=lianqi_costs,
        lianqi_stone_costs=lianqi_stone_costs,
        lianqi_max_spirits=lianqi_max_spirits,
        foundation_base_health=int(st.session_state["draft_foundation_base_health"]),
        foundation_base_attack=int(st.session_state["draft_foundation_base_attack"]),
        foundation_base_defense=int(st.session_state["draft_foundation_base_defense"]),
        foundation_base_cost=int(st.session_state["draft_foundation_base_cost"]),
        foundation_base_stone_cost=int(st.session_state["draft_foundation_base_stone_cost"]),
        foundation_base_max_spirit=int(st.session_state["draft_foundation_base_max_spirit"]),
        resource_level_multiplier=float(st.session_state["draft_resource_level_multiplier"]),
        resource_realm_multiplier=float(st.session_state["draft_resource_realm_multiplier"]),
        stat_level_multiplier=float(st.session_state["draft_stat_level_multiplier"]),
        stat_realm_multiplier=float(st.session_state["draft_stat_realm_multiplier"]),
    )


def _render_summary(df: pd.DataFrame):
    if df.empty:
        return
    spirit_total = float(df["cumulative_spirit_days"].iloc[-1])
    material_total = float(df["cumulative_material_days"].iloc[-1])
    c1, c2 = st.columns(2)
    c1.metric("总灵气耗时（天）", format_number(spirit_total))
    c2.metric("总材料耗时（天）", format_number(material_total))


def _build_compare_html(before_text: str, after_text: str) -> str:
    before = str(before_text)
    after = str(after_text)
    if before == after:
        return html.escape(after)
    return (
        f'<span style="color:#1B5E20">{html.escape(before)}</span>'
        f'→'
        f'<span style="color:#8B0000">{html.escape(after)}</span>'
    )


def _build_compare_number_html(before: float, after: float) -> str:
    return _build_compare_html(format_number(before), format_number(after))


def _render_compare_metrics(items: list[dict]) -> None:
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        with cols[i]:
            st.markdown(
                (
                    f'<div style="font-size:13px;color:#666;margin-bottom:4px;">{html.escape(str(item["label"]))}</div>'
                    f'<div style="font-size:24px;font-weight:600;">{item["value_html"]}</div>'
                ),
                unsafe_allow_html=True,
            )


def _build_realm_max_summary(df: pd.DataFrame, realm_order: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby("realm_name", as_index=False)
        .agg(
            realm_spirit_days=("step_spirit_hours", lambda x: float(x.sum()) / 24.0),
            realm_stone_days=("step_stone_hours", lambda x: float(x.sum()) / 24.0),
            realm_material_days=("step_material_hours", lambda x: float(x.sum()) / 24.0),
        )
    )
    grouped["realm_gathering_days"] = grouped["realm_spirit_days"] + grouped["realm_stone_days"]
    grouped["realm_max_days"] = grouped[["realm_gathering_days", "realm_material_days"]].max(axis=1)
    grouped["realm_spirit_days_display"] = grouped["realm_spirit_days"].map(format_number)
    grouped["realm_stone_days_display"] = grouped["realm_stone_days"].map(format_number)
    grouped["realm_material_days_display"] = grouped["realm_material_days"].map(format_number)
    grouped["realm_max_days_display"] = grouped["realm_max_days"].map(format_number)
    order_rank = {name: i for i, name in enumerate(realm_order)}
    grouped["order_rank"] = grouped["realm_name"].map(lambda x: order_rank.get(x, 999))
    grouped = grouped.sort_values("order_rank").reset_index(drop=True)
    return grouped


def _format_step_or_cumulative_duration(value: float, *, source_unit: str, realm_name: str) -> str:
    if abs(float(value)) < 1e-12:
        return ""
    total_hours = float(value) if source_unit == "hours" else float(value) * 24.0
    if total_hours < 1.0:
        return f"{format_number(total_hours * 60.0)} 分钟"
    if total_hours < 24.0:
        return f"{format_number(total_hours)} 小时"
    return f"{format_number(total_hours / 24.0)} 天"


def _build_realm_summary_display_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary_df.iterrows():
        realm_name = str(row["realm_name"])
        rows.append(
            {
                "大境界": realm_name,
                "该境界灵气总耗时": _format_step_or_cumulative_duration(float(row["realm_spirit_days"]), source_unit="days", realm_name=realm_name),
                "该境界灵石总耗时": _format_step_or_cumulative_duration(float(row["realm_stone_days"]), source_unit="days", realm_name=realm_name),
                "该境界材料总耗时": _format_step_or_cumulative_duration(float(row["realm_material_days"]), source_unit="days", realm_name=realm_name),
                "该境界Max耗时": _format_step_or_cumulative_duration(float(row["realm_max_days"]), source_unit="days", realm_name=realm_name),
            }
        )
    return pd.DataFrame(rows)


def _build_upgrade_detail_display_table(display_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in display_df.iterrows():
        realm_name = str(row["realm_name"])
        rows.append(
            {
                "序号": int(row["step_index"]),
                "从": str(row["from_stage"]),
                "灵石消耗": int(row["spirit_stone_cost"]),
                "灵气消耗": int(row["spirit_energy_cost"]),
                "破境草需求": "" if int(row["foundation_herb_needed"]) == 0 else int(row["foundation_herb_needed"]),
                "层间灵气耗时": _format_step_or_cumulative_duration(float(row["step_spirit_hours"]), source_unit="hours", realm_name=realm_name),
                "层间灵石耗时": _format_step_or_cumulative_duration(float(row["step_stone_hours"]), source_unit="hours", realm_name=realm_name),
                "层间材料耗时": _format_step_or_cumulative_duration(float(row["step_material_hours"]), source_unit="hours", realm_name=realm_name),
                "累计灵气耗时": _format_step_or_cumulative_duration(float(row["cumulative_spirit_days"]), source_unit="days", realm_name=realm_name),
                "累计灵石耗时": _format_step_or_cumulative_duration(float(row["cumulative_stone_days"]), source_unit="days", realm_name=realm_name),
                "累计材料耗时": _format_step_or_cumulative_duration(float(row["cumulative_material_days"]), source_unit="days", realm_name=realm_name),
            }
        )
    return pd.DataFrame(rows)


def _get_normal_area_options(areas_data: dict) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    normal_areas = areas_data.get("normal_areas", {})
    for area_id, area_cfg in normal_areas.items():
        options.append((str(area_id), str(area_cfg.get("name", area_id))))
    return options


def _build_battle_matrix(
    realms_data: dict,
    areas_data: dict,
    enemies_data: dict,
    *,
    k_value: float,
    skill_coef: float,
    trials: int,
    max_fights_per_trial: int,
    battle_interval_seconds: float,
    seed: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = build_checkpoint_matrix(
        realms_data=realms_data,
        areas_data=areas_data,
        enemies_data=enemies_data,
        k_value=k_value,
        skill_coef=skill_coef,
        checkpoints=(1, 5),
        trials=trials,
        max_fights_per_trial=max_fights_per_trial,
        battle_interval_seconds=battle_interval_seconds,
        penetration=0.0,
        seed=seed,
        target_realms=("炼气期", "筑基期", "金丹期"),
    )
    return pd.DataFrame(result["summary_rows"]), pd.DataFrame(result["reward_rows"])


@st.cache_data(show_spinner=False)
def _build_level_max_spirit_stone_gain_map(
    realms_data: dict,
    areas_data: dict,
    enemies_data: dict,
    *,
    k_value: float,
    skill_coef: float,
    battle_interval_seconds: float,
) -> dict[str, float]:
    normal_areas = areas_data.get("normal_areas", {})
    gain_map: dict[str, float] = {}
    for realm_name in realms_data.get("realm_order", []):
        max_level = int(realms_data.get("realms", {}).get(realm_name, {}).get("max_level", 0))
        for level in range(1, max_level + 1):
            player_attrs = build_player_attrs_from_realm(realms_data, realm_name, level)
            best_spirit_stone_per_hour = 0.0
            for _, area_cfg in normal_areas.items():
                avg_result = simulate_average(
                    player_attrs=player_attrs,
                    area_cfg=area_cfg,
                    enemies_data=enemies_data,
                    k_value=k_value,
                    skill_coef=skill_coef,
                    penetration=0.0,
                    trials=DEFAULT_TRIALS,
                    max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
                    battle_interval_seconds=battle_interval_seconds,
                    seed=FIXED_BATTLE_RANDOM_SEED,
                )
                spirit_stone_per_hour = float(avg_result.get("avg_item_per_hour", {}).get("spirit_stone", 0.0))
                if spirit_stone_per_hour > best_spirit_stone_per_hour:
                    best_spirit_stone_per_hour = spirit_stone_per_hour
            gain_map[f"{realm_name}:{level}"] = best_spirit_stone_per_hour
    return gain_map


def _format_stage_name(realms_data: dict, realm_name: str, level: int) -> str:
    level_names = realms_data.get("realms", {}).get(realm_name, {}).get("level_names", {})
    return f"{realm_name}{level_names.get(str(level), f'第{level}层')}"


def _check_foundation_cave_min_pass(
    realms_data: dict,
    areas_data: dict,
    enemies_data: dict,
    *,
    k_value: float,
    skill_coef: float,
    battle_interval_seconds: float,
) -> dict:
    daily_area = areas_data.get("daily_areas", {}).get("foundation_herb_cave")
    if not daily_area:
        return {"exists": False}

    lianqi_cfg = realms_data.get("realms", {}).get("炼气期", {})
    lianqi_max = int(lianqi_cfg.get("max_level", 10))
    start_player = build_player_attrs_from_realm(realms_data, "炼气期", lianqi_max)
    start_result = simulate_trial(
        player_attrs=start_player,
        area_cfg=daily_area,
        enemies_data=enemies_data,
        k_value=k_value,
        skill_coef=skill_coef,
        penetration=0.0,
        max_fights_per_trial=1,
        battle_interval_seconds=battle_interval_seconds,
        seed=FIXED_BATTLE_RANDOM_SEED,
    )
    start_pass = int(start_result.get("victory_count", 0)) >= 1
    if not start_pass:
        return {
            "exists": True,
            "can_lianqi_max": False,
            "lianqi_max_stage": _format_stage_name(realms_data, "炼气期", lianqi_max),
        }

    min_pass_level = lianqi_max
    for level in range(lianqi_max - 1, 0, -1):
        player = build_player_attrs_from_realm(realms_data, "炼气期", level)
        result = simulate_trial(
            player_attrs=player,
            area_cfg=daily_area,
            enemies_data=enemies_data,
            k_value=k_value,
            skill_coef=skill_coef,
            penetration=0.0,
            max_fights_per_trial=1,
            battle_interval_seconds=battle_interval_seconds,
            seed=FIXED_BATTLE_RANDOM_SEED,
        )
        if int(result.get("victory_count", 0)) >= 1:
            min_pass_level = level
        else:
            break

    return {
        "exists": True,
        "can_lianqi_max": True,
        "lianqi_max_stage": _format_stage_name(realms_data, "炼气期", lianqi_max),
        "min_pass_stage": _format_stage_name(realms_data, "炼气期", min_pass_level),
    }


def _build_tower_stage_max_floor_table(
    realms_data: dict,
    areas_data: dict,
    enemies_data: dict,
    *,
    k_value: float,
    skill_coef: float,
    battle_interval_seconds: float,
) -> pd.DataFrame:
    rows = build_tower_max_floor_by_stage(
        realms_data=realms_data,
        areas_data=areas_data,
        enemies_data=enemies_data,
        k_value=k_value,
        skill_coef=skill_coef,
        penetration=0.0,
        battle_interval_seconds=battle_interval_seconds,
        seed=FIXED_BATTLE_RANDOM_SEED,
        target_realms=("筑基期", "金丹期"),
    )
    table_rows = []
    for row in rows:
        realm_name = str(row.get("realm_name", ""))
        level = int(row.get("level", 1))
        table_rows.append(
            {
                "境界层级": _format_stage_name(realms_data, realm_name, level),
                "最大可通关层": int(row.get("max_pass_floor", 0)),
            }
        )
    return pd.DataFrame(table_rows)


def _build_item_name_map(items_data: dict, recipes_data: dict) -> dict[str, str]:
    item_name_map: dict[str, str] = {}
    for item_id, item_cfg in items_data.get("items", {}).items():
        item_name_map[str(item_id)] = str(item_cfg.get("name", item_id))
    for recipe_id, recipe_cfg in recipes_data.get("recipes", {}).items():
        item_name_map.setdefault(str(recipe_id), str(recipe_cfg.get("name", recipe_id)))
    item_name_map.setdefault("spirit_stone", "灵石")
    return item_name_map


def _format_reward_cell(reward_items: dict[str, float], item_name_map: dict[str, str]) -> str:
    if not reward_items:
        return "-"
    parts = []
    for item_id in sorted(reward_items.keys()):
        name = item_name_map.get(item_id, item_id)
        parts.append(f"{name}: {format_number(reward_items[item_id])}")
    return "，".join(parts)


def _split_reward_cells(reward_items: dict[str, float], item_name_map: dict[str, str]) -> tuple[str, str]:
    spirit_value = float(reward_items.get("spirit_stone", 0.0))
    spirit_text = format_number(spirit_value) if spirit_value > 0.0 else ""
    other_parts = []
    for item_id in sorted(reward_items.keys()):
        if item_id == "spirit_stone":
            continue
        value = float(reward_items[item_id])
        if value <= 0.0:
            continue
        item_name = item_name_map.get(item_id, item_id)
        other_parts.append(f"{item_name}: {format_number(value)}")
    return spirit_text, "，".join(other_parts)


def _render_battle_matrix_compare_html(before_rows: list[dict], after_rows: list[dict]) -> None:
    if not after_rows:
        st.info("暂无可展示的数据。")
        return

    before_map = {(str(r["stage"]), str(r["area"])): r for r in before_rows}
    before_stage_map = {str(r["stage"]): r for r in before_rows}
    after_stage_map = {str(r["stage"]): r for r in after_rows}

    rowspans: dict[str, int] = {}
    for row in after_rows:
        stage = str(row["stage"])
        rowspans[stage] = rowspans.get(stage, 0) + 1

    rendered_stage: dict[str, bool] = {}
    html_rows = []
    for row in after_rows:
        stage = str(row["stage"])
        area = str(row["area"])
        before_row = before_map.get((stage, area), {})
        cells = []
        if not rendered_stage.get(stage, False):
            before_stage_row = before_stage_map.get(stage, {})
            after_stage_row = after_stage_map.get(stage, row)
            cells.append(
                f'<td rowspan="{rowspans[stage]}" style="vertical-align: middle; text-align: center; white-space: nowrap;">'
                f"{html.escape(stage)}</td>"
            )
            cells.append(
                f'<td rowspan="{rowspans[stage]}" style="vertical-align: middle; text-align: center; white-space: nowrap;">'
                f'{_build_compare_html(str(before_stage_row.get("max_spirit", after_stage_row.get("max_spirit", ""))), str(after_stage_row.get("max_spirit", "")))}'
                f"</td>"
            )
            rendered_stage[stage] = True
        cells.append(f'<td style="text-align: center;">{html.escape(area)}</td>')
        cells.append(
            f'<td style="text-align: center;">'
            f'{_build_compare_html(str(before_row.get("avg_fights", row["avg_fights"])), str(row["avg_fights"]))}'
            f"</td>"
        )
        cells.append(
            f'<td style="text-align: center;">'
            f'{_build_compare_html(str(before_row.get("efficiency", row["efficiency"])), str(row["efficiency"]))}'
            f"</td>"
        )
        cells.append(
            f'<td style="text-align: center;">'
            f'{_build_compare_html(str(before_row.get("spirit", row["spirit"])), str(row["spirit"]))}'
            f"</td>"
        )
        cells.append(
            f'<td style="text-align: left;">'
            f'{_build_compare_html(str(before_row.get("others", row["others"])), str(row["others"]))}'
            f"</td>"
        )
        html_rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = f"""
<table style="width:100%; border-collapse: collapse;">
  <thead>
    <tr>
      <th style="border:1px solid #ddd; padding:6px; text-align:center;">大境界层级</th>
      <th style="border:1px solid #ddd; padding:6px; text-align:center;">最大每小时灵石获取量</th>
      <th style="border:1px solid #ddd; padding:6px; text-align:center;">区域</th>
      <th style="border:1px solid #ddd; padding:6px; text-align:center;">平均战斗次数</th>
      <th style="border:1px solid #ddd; padding:6px; text-align:center;">平均战斗效率<br>（次/小时）</th>
      <th style="border:1px solid #ddd; padding:6px; text-align:center;">灵石掉落数量<br>（每小时）</th>
      <th style="border:1px solid #ddd; padding:6px; text-align:left;">其他掉落期望数量<br>（每小时）</th>
    </tr>
  </thead>
  <tbody>
    {''.join(html_rows)}
  </tbody>
</table>
"""
    st.markdown(table_html, unsafe_allow_html=True)


def _render_table_html(df: pd.DataFrame, numeric_columns: list[str]) -> None:
    if df.empty:
        st.info("暂无数据。")
        return

    def _header_html(label: str) -> str:
        safe = html.escape(str(label))
        safe = safe.replace("（小时）", "<br>（小时）")
        safe = safe.replace("（天）", "<br>（天）")
        safe = safe.replace("(小时)", "<br>(小时)")
        safe = safe.replace("(天)", "<br>(天)")
        return safe

    headers = "".join(
        f'<th style="border:1px solid #ddd; padding:6px; text-align:center;">{_header_html(str(col))}</th>'
        for col in df.columns
    )
    body_rows = []
    for _, row in df.iterrows():
        row_cells = []
        for col in df.columns:
            align = "center"
            row_cells.append(
                f'<td style="border:1px solid #ddd; padding:6px; text-align:{align};">{html.escape(str(row[col]))}</td>'
            )
        body_rows.append("<tr>" + "".join(row_cells) + "</tr>")

    table_html = f"""
<table style="width:100%; border-collapse: collapse;">
  <thead><tr>{headers}</tr></thead>
  <tbody>{''.join(body_rows)}</tbody>
</table>
"""
    st.markdown(table_html, unsafe_allow_html=True)


def _render_compare_table_html(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    numeric_columns: list[str],
) -> None:
    if before_df.empty and after_df.empty:
        st.info("暂无数据。")
        return
    if before_df.empty:
        _render_table_html(after_df, numeric_columns=numeric_columns)
        return
    if after_df.empty:
        _render_table_html(before_df, numeric_columns=numeric_columns)
        return

    def _header_html(label: str) -> str:
        safe = html.escape(str(label))
        safe = safe.replace("（小时）", "<br>（小时）")
        safe = safe.replace("（天）", "<br>（天）")
        safe = safe.replace("(小时)", "<br>(小时)")
        safe = safe.replace("(天)", "<br>(天)")
        return safe

    headers = "".join(
        f'<th style="border:1px solid #ddd; padding:6px; text-align:center;">{_header_html(str(col))}</th>'
        for col in after_df.columns
    )
    body_rows = []
    row_count = min(len(before_df), len(after_df))
    for idx in range(row_count):
        row_before = before_df.iloc[idx]
        row_after = after_df.iloc[idx]
        row_cells = []
        for col in after_df.columns:
            align = "center"
            before_text = str(row_before[col]) if col in before_df.columns else ""
            after_text = str(row_after[col])
            if col in numeric_columns:
                cell_html = _build_compare_html(before_text, after_text)
            else:
                cell_html = html.escape(after_text)
            row_cells.append(
                f'<td style="border:1px solid #ddd; padding:6px; text-align:{align};">{cell_html}</td>'
            )
        body_rows.append("<tr>" + "".join(row_cells) + "</tr>")

    table_html = f"""
<table style="width:100%; border-collapse: collapse;">
  <thead><tr>{headers}</tr></thead>
  <tbody>{''.join(body_rows)}</tbody>
</table>
"""
    st.markdown(table_html, unsafe_allow_html=True)


base_realms_data, base_recipes_data, base_areas_data, base_enemies_data, base_items_data = _load_data()
_init_realm_draft_state(base_realms_data)
_init_recipe_draft_state(base_recipes_data)
_init_areas_draft_state(base_areas_data)
_init_enemy_draft_state(base_enemies_data)
item_name_map = _build_item_name_map(base_items_data, base_recipes_data)

draft_realms = _build_draft_realms(base_realms_data)
draft_recipes = _build_draft_recipes(base_recipes_data, st.session_state["draft_high_tier_recipe_rows"])
draft_areas = _build_draft_areas(base_areas_data)
draft_enemies = _build_draft_enemies(base_enemies_data, st.session_state["draft_enemy_template_rows"])
base_stone_gain_map = _build_level_max_spirit_stone_gain_map(
    realms_data=base_realms_data,
    areas_data=base_areas_data,
    enemies_data=base_enemies_data,
    k_value=DEFAULT_K_VALUE,
    skill_coef=1.0,
    battle_interval_seconds=5.0,
)
draft_stone_gain_map = _build_level_max_spirit_stone_gain_map(
    realms_data=draft_realms,
    areas_data=draft_areas,
    enemies_data=draft_enemies,
    k_value=DEFAULT_K_VALUE,
    skill_coef=1.0,
    battle_interval_seconds=5.0,
)
base_display_df = _prepare_display_df(
    build_time_rows_with_stone_gain(
        realms_data=base_realms_data,
        recipes_data=base_recipes_data,
        stone_gain_per_hour_map=base_stone_gain_map,
    )
)
draft_display_df = _prepare_display_df(
    build_time_rows_with_stone_gain(
        realms_data=draft_realms,
        recipes_data=draft_recipes,
        stone_gain_per_hour_map=draft_stone_gain_map,
    )
)

PAGE_LABELS = {
    "cultivation": "修炼建模可视化",
    "battle": "战斗建模可视化",
    "areas": "历练区域配置（areas）",
    "realms": "境界配置（realms）",
    "enemies": "敌人模板配置（enemies）",
    "recipes": "丹方配置（recipes）",
}
SIDEBAR_GROUPS = [
    ("建模页面", [("📈", "cultivation"), ("⚔️", "battle")]),
    ("配置工具", [("🧭", "areas"), ("🪷", "realms"), ("🐺", "enemies"), ("🧪", "recipes")]),
]

if "current_page_key" not in st.session_state or st.session_state["current_page_key"] not in PAGE_LABELS:
    st.session_state["current_page_key"] = "cultivation"
current_page_key = st.session_state["current_page_key"]

with st.sidebar:
    st.markdown(
        """
<style>
[data-testid="stSidebar"] {
    background: #eef0f5;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
.ic-nav-title {
    font-size: 13px;
    font-weight: 700;
    color: #4a4f5a;
    margin: 14px 0 8px 0;
}
[data-testid="stSidebar"] div.stButton > button {
    width: 100%;
    border-radius: 8px;
    padding: 8px 10px;
    margin: 2px 0;
    border: none;
    background: transparent;
    color: #495057;
    font-size: 15px;
    justify-content: flex-start;
    text-align: left;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background: #dfe4ef;
    color: #2f3540;
}
[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
    background: #d9deea;
    color: #222831;
    font-weight: 700;
}
</style>
""",
        unsafe_allow_html=True,
    )
    st.markdown("### 页面")
    for group_title, items in SIDEBAR_GROUPS:
        st.markdown(f'<div class="ic-nav-title">{html.escape(group_title)}</div>', unsafe_allow_html=True)
        for icon, key in items:
            label = PAGE_LABELS[key].replace("可视化", "")
            if st.button(
                f"{icon}  {label}",
                key=f"sidebar_nav_{key}",
                type="primary" if key == current_page_key else "secondary",
                use_container_width=True,
            ):
                current_page_key = key
                st.session_state["current_page_key"] = current_page_key
                st.rerun()

page = PAGE_LABELS[current_page_key]

if page == "修炼建模可视化":
    st.caption("当前页面展示的是“草稿预览效果”，包含未保存到文件的配置改动。")
    st.caption("材料获取速率固定：foundation_herb = 30 / 天")
    if not base_display_df.empty and not draft_display_df.empty:
        _render_compare_metrics(
            [
                {
                    "label": "总灵气耗时（天）",
                    "value_html": _build_compare_number_html(
                        float(base_display_df["cumulative_spirit_days"].iloc[-1]),
                        float(draft_display_df["cumulative_spirit_days"].iloc[-1]),
                    ),
                },
                {
                    "label": "总材料耗时（天）",
                    "value_html": _build_compare_number_html(
                        float(base_display_df["cumulative_material_days"].iloc[-1]),
                        float(draft_display_df["cumulative_material_days"].iloc[-1]),
                    ),
                },
            ]
        )

    st.subheader("大境界耗时汇总（Max）")
    st.caption("时间单位规则：小于1小时显示分钟；小于1天显示小时；其余显示天。")
    before_realm_summary_df = _build_realm_max_summary(base_display_df, base_realms_data["realm_order"])
    after_realm_summary_df = _build_realm_max_summary(draft_display_df, draft_realms["realm_order"])
    if not after_realm_summary_df.empty:
        before_summary_table = _build_realm_summary_display_table(before_realm_summary_df)
        after_summary_table = _build_realm_summary_display_table(after_realm_summary_df)
        _render_compare_table_html(
            before_summary_table,
            after_summary_table,
            numeric_columns=["该境界灵气总耗时", "该境界灵石总耗时", "该境界材料总耗时", "该境界Max耗时"],
        )

    st.subheader("升级明细")
    st.caption("时间单位规则：小于1小时显示分钟；小于1天显示小时；其余显示天。")
    before_table_df = _build_upgrade_detail_display_table(base_display_df)
    after_table_df = _build_upgrade_detail_display_table(draft_display_df)
    _render_compare_table_html(
        before_table_df,
        after_table_df,
        numeric_columns=[
            "序号",
            "灵石消耗",
            "灵气消耗",
            "破境草需求",
            "层间灵气耗时",
            "层间灵石耗时",
            "层间材料耗时",
            "累计灵气耗时",
            "累计灵石耗时",
            "累计材料耗时",
        ],
    )

elif page == "境界配置（realms）":
    st.subheader("生成参数（realms.json 相关）")
    attr_col, res_col = st.columns(2)
    with attr_col:
        st.markdown("**属性（筑基1层基准 + 属性倍率）**")
        narrow, _ = st.columns([3, 2])
        with narrow:
            page2_base_health = int(st.number_input(
                "health 基准",
                min_value=1,
                value=int(st.session_state.get("draft_foundation_base_health", 1)),
                step=1,
                key="page2_foundation_base_health",
            ))
            st.session_state["draft_foundation_base_health"] = page2_base_health

            page2_base_attack = int(st.number_input(
                "attack 基准",
                min_value=1,
                value=int(st.session_state.get("draft_foundation_base_attack", 1)),
                step=1,
                key="page2_foundation_base_attack",
            ))
            st.session_state["draft_foundation_base_attack"] = page2_base_attack

            page2_base_defense = int(st.number_input(
                "defense 基准",
                min_value=1,
                value=int(st.session_state.get("draft_foundation_base_defense", 1)),
                step=1,
                key="page2_foundation_base_defense",
            ))
            st.session_state["draft_foundation_base_defense"] = page2_base_defense

            page2_stat_level_mult = float(st.number_input(
                "层内递推倍率",
                min_value=1.00,
                value=float(st.session_state.get("draft_stat_level_multiplier", 1.0)),
                step=0.01,
                format="%.2f",
                key="page2_stat_level_multiplier",
            ))
            st.session_state["draft_stat_level_multiplier"] = page2_stat_level_mult

            page2_stat_realm_mult = float(st.number_input(
                "跨大境界首层倍率",
                min_value=1.00,
                value=float(st.session_state.get("draft_stat_realm_multiplier", 1.0)),
                step=0.10,
                format="%.2f",
                key="page2_stat_realm_multiplier",
            ))
            st.session_state["draft_stat_realm_multiplier"] = page2_stat_realm_mult
            if (page2_stat_level_mult ** 9) >= page2_stat_realm_mult:
                st.markdown(
                    '<span style="color:#c62828;">提示：属性层内递推倍率的9次方应小于属性跨大境界首层倍率。</span>',
                    unsafe_allow_html=True,
                )

    with res_col:
        st.markdown("**资源（筑基1层基准 + 资源倍率）**")
        narrow, _ = st.columns([3, 2])
        with narrow:
            page2_base_cost = int(st.number_input(
                "spirit_energy_cost 基准",
                min_value=1,
                value=int(st.session_state.get("draft_foundation_base_cost", 1)),
                step=1,
                key="page2_foundation_base_cost",
            ))
            st.session_state["draft_foundation_base_cost"] = page2_base_cost

            page2_base_stone_cost = int(st.number_input(
                "spirit_stone_cost 基准",
                min_value=1,
                value=int(st.session_state.get("draft_foundation_base_stone_cost", 1)),
                step=1,
                key="page2_foundation_base_stone_cost",
            ))
            st.session_state["draft_foundation_base_stone_cost"] = page2_base_stone_cost

            page2_base_max = int(st.number_input(
                "max_spirit_energy 基准",
                min_value=1,
                value=int(st.session_state.get("draft_foundation_base_max_spirit", 1)),
                step=1,
                key="page2_foundation_base_max_spirit",
            ))
            st.session_state["draft_foundation_base_max_spirit"] = page2_base_max

            page2_resource_level_mult = float(st.number_input(
                "层内递推倍率",
                min_value=1.00,
                value=float(st.session_state.get("draft_resource_level_multiplier", 1.0)),
                step=0.01,
                format="%.2f",
                key="page2_resource_level_multiplier",
            ))
            st.session_state["draft_resource_level_multiplier"] = page2_resource_level_mult

            page2_resource_realm_mult = float(st.number_input(
                "跨大境界首层倍率",
                min_value=1.00,
                value=float(st.session_state.get("draft_resource_realm_multiplier", 1.0)),
                step=0.10,
                format="%.2f",
                key="page2_resource_realm_multiplier",
            ))
            st.session_state["draft_resource_realm_multiplier"] = page2_resource_realm_mult
            if (page2_resource_level_mult ** 9) >= page2_resource_realm_mult:
                st.markdown(
                    '<span style="color:#c62828;">提示：资源层内递推倍率的9次方应小于资源跨大境界首层倍率。</span>',
                    unsafe_allow_html=True,
                )

    st.subheader("炼气期手动编辑（保留手动值）")
    lianqi_editor_key = "page2_lianqi_editor"
    edited_lianqi_df = st.data_editor(
        pd.DataFrame(st.session_state["draft_lianqi_rows"]),
        hide_index=True,
        use_container_width=True,
        disabled=["层级"],
        key=lianqi_editor_key,
    )
    st.session_state["draft_lianqi_rows"] = edited_lianqi_df.to_dict("records")

    if st.button("保存 realms 配置", type="primary"):
        latest_base_realms = load_json(REALMS_PATH)
        latest_draft_realms = _build_draft_realms(latest_base_realms)
        save_realms_numeric_fields_preserve_format(
            path=REALMS_PATH,
            old_data=latest_base_realms,
            new_data=latest_draft_realms,
        )
        st.success(f"已保存：{REALMS_PATH}")

elif page == "历练区域配置（areas）":
    st.subheader("普通历练区域配置")
    st.caption("上表用于批量改区域名称和默认连续历练；下方用于精细调整所选区域的描述、敌人池和掉落。")
    st.caption("当前页仅编辑 `normal_areas`，因为战斗建模页当前只消费普通历练区域。")

    area_overview_df = _get_normal_area_editor_df(
        st.session_state["draft_areas_data"],
        item_name_map,
        base_areas_data=base_areas_data,
    )
    area_overview_editor_key = "page_area_overview_editor"
    edited_area_df = st.data_editor(
        area_overview_df,
        hide_index=True,
        use_container_width=True,
        disabled=["area_id", "敌人池数量", "权重总和", "敌人等级范围", "掉落种类", "理论最大灵石掉落效率（每小时）"],
        column_config={
            "area_id": st.column_config.TextColumn("area_id"),
            "区域名称": st.column_config.TextColumn("区域名称"),
            "默认连续历练": st.column_config.CheckboxColumn("默认连续历练"),
            "敌人池数量": st.column_config.NumberColumn("敌人池数量"),
            "权重总和": st.column_config.NumberColumn("权重总和"),
            "敌人等级范围": st.column_config.TextColumn("敌人等级范围"),
            "掉落种类": st.column_config.TextColumn("掉落种类"),
            "理论最大灵石掉落效率（每小时）": st.column_config.TextColumn("理论最大灵石掉落效率（每小时）"),
        },
        key=area_overview_editor_key,
    )

    draft_areas_data = deepcopy(st.session_state["draft_areas_data"])
    normal_areas = draft_areas_data.setdefault("normal_areas", {})
    for _, row in edited_area_df.iterrows():
        area_id = str(row["area_id"])
        area_cfg = normal_areas.get(area_id)
        if area_cfg is None:
            continue
        area_cfg["id"] = area_id
        area_cfg["name"] = str(row["区域名称"]).strip() or area_id
        area_cfg["default_continuous"] = bool(row["默认连续历练"])
    st.session_state["draft_areas_data"] = draft_areas_data

    area_options = _get_normal_area_options(st.session_state["draft_areas_data"])
    if not area_options:
        st.warning("当前没有普通历练区域可编辑。")
    else:
        area_label_to_id = {f"{name} ({area_id})": area_id for area_id, name in area_options}
        current_area_id = st.session_state.get("draft_area_selected_area_id", area_options[0][0])
        if current_area_id not in dict(area_options):
            current_area_id = area_options[0][0]
            st.session_state["draft_area_selected_area_id"] = current_area_id
            st.session_state["draft_area_selected_template_index"] = 0
        selected_area_label = next(
            (label for label, area_id in area_label_to_id.items() if area_id == current_area_id),
            next(iter(area_label_to_id.keys())),
        )
        st.header("当前区域配置")
        selected_area_label = st.selectbox(
            "选择区域",
            options=list(area_label_to_id.keys()),
            index=list(area_label_to_id.keys()).index(selected_area_label),
            key="page_area_selected_area_label",
        )
        selected_area_id = area_label_to_id[selected_area_label]
        st.session_state["draft_area_selected_area_id"] = selected_area_id

        draft_areas_data = deepcopy(st.session_state["draft_areas_data"])
        selected_area_cfg = draft_areas_data["normal_areas"][selected_area_id]

        selected_area_cfg["description"] = st.text_area(
            "区域描述",
            value=str(selected_area_cfg.get("description", "")),
            height=90,
            key=f"page_area_description_{selected_area_id}",
        )
        st.session_state["draft_areas_data"] = draft_areas_data

        enemy_name_map = _build_enemy_name_map(draft_enemies)
        template_df = _get_area_template_editor_df(selected_area_cfg, enemy_name_map, item_name_map)
        template_editor_key = f"page_area_template_editor_{selected_area_id}"
        template_rows_state_key = f"draft_area_template_rows_{selected_area_id}"
        if template_rows_state_key not in st.session_state:
            st.session_state[template_rows_state_key] = template_df.to_dict("records")
        source_template_df = pd.DataFrame(st.session_state.get(template_rows_state_key, template_df.to_dict("records")))
        edited_template_df = st.data_editor(
            source_template_df,
            hide_index=True,
            use_container_width=True,
            disabled=["序号", "敌人名称", "掉落摘要"],
            column_config={
                "序号": st.column_config.NumberColumn("序号"),
                "敌人模板": st.column_config.SelectboxColumn("敌人模板", options=sorted(enemy_name_map.keys())),
                "敌人名称": st.column_config.TextColumn("敌人名称"),
                "等级下限": st.column_config.NumberColumn("等级下限", min_value=1, step=1),
                "等级上限": st.column_config.NumberColumn("等级上限", min_value=1, step=1),
                "权重": st.column_config.NumberColumn("权重", min_value=0, step=1),
                "掉落摘要": st.column_config.TextColumn("掉落摘要"),
            },
            key=template_editor_key,
        )
        st.session_state[template_rows_state_key] = edited_template_df.to_dict("records")

        existing_templates = list(selected_area_cfg.get("enemies_template", []))
        normalized_templates = []
        for row_idx, (_, row) in enumerate(edited_template_df.iterrows()):
            template_id = str(row["敌人模板"]).strip()
            if not template_id:
                continue
            min_level = max(1, int(float(row["等级下限"])))
            max_level = max(min_level, int(float(row["等级上限"])))
            old_template = existing_templates[row_idx] if row_idx < len(existing_templates) else {}
            normalized_templates.append(
                {
                    "enemies": [
                        {
                            "template": template_id,
                            "min_level": min_level,
                            "max_level": max_level,
                        }
                    ],
                    "weight": max(0, int(float(row["权重"]))),
                    "drops": deepcopy(old_template.get("drops", {})),
                }
            )

        draft_areas_data = deepcopy(st.session_state["draft_areas_data"])
        selected_area_cfg = draft_areas_data["normal_areas"][selected_area_id]
        selected_area_cfg["enemies_template"] = normalized_templates
        st.session_state["draft_areas_data"] = draft_areas_data

        if not normalized_templates:
            st.info("该区域当前没有可编辑的敌人池。")
        else:
            template_options = []
            for idx, template_cfg in enumerate(normalized_templates):
                enemy_desc = template_cfg["enemies"][0]
                template_id = str(enemy_desc.get("template", ""))
                template_options.append(
                    f"第{idx + 1}条：{enemy_name_map.get(template_id, template_id)} / Lv.{enemy_desc.get('min_level', 1)}-{enemy_desc.get('max_level', 1)} / 权重{template_cfg.get('weight', 0)}"
                )
            current_template_index = int(st.session_state.get("draft_area_selected_template_index", 0))
            current_template_index = min(max(current_template_index, 0), len(template_options) - 1)
            selected_template_label = st.selectbox(
                "编辑掉落的敌人池",
                options=template_options,
                index=current_template_index,
                key=f"page_area_selected_template_{selected_area_id}",
            )
            selected_template_index = template_options.index(selected_template_label)
            st.session_state["draft_area_selected_template_index"] = selected_template_index

            drop_df = _get_area_drop_editor_df(
                st.session_state["draft_areas_data"]["normal_areas"][selected_area_id],
                selected_template_index,
                item_name_map,
            )
            drop_editor_key = f"page_area_drop_editor_{selected_area_id}_{selected_template_index}"
            edited_drop_df = st.data_editor(
                drop_df,
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",
                disabled=["掉落名称"],
                column_config={
                    "删除": st.column_config.CheckboxColumn("删除"),
                    "item_id": st.column_config.SelectboxColumn("item_id", options=sorted(item_name_map.keys())),
                    "掉落名称": st.column_config.TextColumn("掉落名称"),
                    "min": st.column_config.NumberColumn("最小数量", min_value=0, step=1),
                    "max": st.column_config.NumberColumn("最大数量", min_value=0, step=1),
                    "chance": st.column_config.NumberColumn("概率", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"),
                },
                key=drop_editor_key,
            )

            if st.button("删除勾选行", key=f"page_area_drop_delete_rows_btn_{selected_area_id}_{selected_template_index}"):
                filtered_df = edited_drop_df[~edited_drop_df["删除"].fillna(False)].copy()
                filtered_df["删除"] = False
                draft_areas_data = deepcopy(st.session_state["draft_areas_data"])
                normalized_after_delete = {}
                for _, row in filtered_df.iterrows():
                    item_raw = row.get("item_id", "")
                    if item_raw is None or (isinstance(item_raw, str) and item_raw.strip() == "") or pd.isna(item_raw):
                        continue
                    item_id = str(item_raw).strip()
                    if not item_id:
                        continue
                    min_amount = max(0, int(float(row.get("min", 1) or 1)))
                    max_amount = max(min_amount, int(float(row.get("max", min_amount) or min_amount)))
                    chance = min(1.0, max(0.0, float(row.get("chance", 1.0) or 1.0)))
                    normalized_after_delete[item_id] = {"min": min_amount, "max": max_amount, "chance": chance}
                draft_areas_data["normal_areas"][selected_area_id]["enemies_template"][selected_template_index]["drops"] = normalized_after_delete
                st.session_state["draft_areas_data"] = draft_areas_data
                st.rerun()

            def _safe_float(value, default: float) -> float:
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    return default
                if pd.isna(value):
                    return default
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default

            normalized_drops = {}
            for _, row in edited_drop_df.iterrows():
                item_raw = row.get("item_id", "")
                if item_raw is None or (isinstance(item_raw, str) and item_raw.strip() == "") or pd.isna(item_raw):
                    continue
                item_id = str(item_raw).strip()
                if not item_id:
                    continue
                if bool(row.get("删除", False)):
                    continue

                min_raw = row.get("min", None)
                max_raw = row.get("max", None)
                chance_raw = row.get("chance", None)
                # 新增行仅选中 item_id 时，自动给默认值：min=1 max=1 chance=1.0
                min_default = 1.0 if (min_raw is None or (isinstance(min_raw, str) and min_raw.strip() == "") or pd.isna(min_raw)) else 0.0
                min_amount = max(0, int(_safe_float(min_raw, min_default)))
                max_default = float(min_amount) if not (max_raw is None or (isinstance(max_raw, str) and max_raw.strip() == "") or pd.isna(max_raw)) else 1.0
                max_amount = max(min_amount, int(_safe_float(max_raw, max_default)))
                chance_default = 1.0 if (chance_raw is None or (isinstance(chance_raw, str) and chance_raw.strip() == "") or pd.isna(chance_raw)) else 0.0
                chance = min(1.0, max(0.0, _safe_float(chance_raw, chance_default)))
                normalized_drops[item_id] = {
                    "min": min_amount,
                    "max": max_amount,
                    "chance": chance,
                }

            draft_areas_data = deepcopy(st.session_state["draft_areas_data"])
            draft_areas_data["normal_areas"][selected_area_id]["enemies_template"][selected_template_index]["drops"] = normalized_drops
            st.session_state["draft_areas_data"] = draft_areas_data

        if st.button("保存 areas 配置", type="primary"):
            latest_base_areas = load_json(AREAS_PATH)
            latest_base_areas["normal_areas"] = deepcopy(st.session_state["draft_areas_data"].get("normal_areas", {}))
            save_json(AREAS_PATH, latest_base_areas)
            st.success(f"已保存：{AREAS_PATH}")

elif page == "敌人模板配置（enemies）":
    st.subheader("敌人模板成长配置")
    st.caption("可修改每个模板的：生命/攻击/防御基值，以及三项增长率。")
    st.markdown(
        """
<style>
div[data-testid="stDataEditor"] [role="columnheader"] {
    text-align: center !important;
    justify-content: center !important;
}
div[data-testid="stDataEditor"] [role="gridcell"] {
    text-align: center !important;
}
div[data-testid="stDataEditor"] table thead th,
div[data-testid="stDataEditor"] table tbody td,
div[data-testid="stDataEditor"] table tbody td div,
div[data-testid="stDataEditor"] table tbody td input {
    text-align: center !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    enemy_df = pd.DataFrame(st.session_state["draft_enemy_template_rows"])
    enemy_editor_key = "page_enemy_template_editor"
    edited_enemy_df = st.data_editor(
        enemy_df,
        hide_index=True,
        use_container_width=True,
        disabled=["template_id", "敌人名称"],
        column_config={
            "template_id": st.column_config.TextColumn("template_id"),
            "敌人名称": st.column_config.TextColumn("敌人名称"),
            "health_base": st.column_config.NumberColumn("生命基值", min_value=0, step=1),
            "attack_base": st.column_config.NumberColumn("攻击基值", min_value=0, step=1),
            "defense_base": st.column_config.NumberColumn("防御基值", min_value=0, step=1),
            "health_growth": st.column_config.NumberColumn("生命增长率", min_value=0.0, step=0.01, format="%.4f"),
            "attack_growth": st.column_config.NumberColumn("攻击增长率", min_value=0.0, step=0.01, format="%.4f"),
            "defense_growth": st.column_config.NumberColumn("防御增长率", min_value=0.0, step=0.01, format="%.4f"),
        },
        key=enemy_editor_key,
    )
    # 编辑态不做即时强制清洗，避免首次回车后被回写覆盖。
    st.session_state["draft_enemy_template_rows"] = edited_enemy_df.to_dict("records")

    if st.button("保存 enemies 配置", type="primary"):
        normalized_rows = []
        for row in st.session_state["draft_enemy_template_rows"]:
            normalized_rows.append(
                {
                    "template_id": str(row["template_id"]),
                    "敌人名称": str(row["敌人名称"]),
                    "health_base": max(0, int(float(row["health_base"]))),
                    "attack_base": max(0, int(float(row["attack_base"]))),
                    "defense_base": max(0, int(float(row["defense_base"]))),
                    "health_growth": max(0.0, float(row["health_growth"])),
                    "attack_growth": max(0.0, float(row["attack_growth"])),
                    "defense_growth": max(0.0, float(row["defense_growth"])),
                }
            )
        st.session_state["draft_enemy_template_rows"] = normalized_rows
        latest_base_enemies = load_json(ENEMIES_PATH)
        latest_draft_enemies = _build_draft_enemies(latest_base_enemies, normalized_rows)
        save_json(ENEMIES_PATH, latest_draft_enemies)
        st.success(f"已保存：{ENEMIES_PATH}")

elif page == "丹方配置（recipes）":
    st.subheader("高阶破境丹方配置")
    st.caption("仅支持修改：低阶丹药数量与破境草数量（必须为正整数）。")

    c1, c2, c3 = st.columns([1.2, 1.0, 1.0])
    with c1:
        batch_target = st.selectbox(
            "批量修改字段",
            options=["低阶丹药数量", "破境草数量"],
            key="page3_batch_target",
        )
    with c2:
        batch_value = int(
            st.number_input(
                "批量值",
                min_value=1,
                value=1,
                step=1,
                key="page3_batch_value",
            )
        )
    with c3:
        st.write("")
        st.write("")
        if st.button("应用到全部高阶丹方", key="page3_apply_batch"):
            updated_rows = []
            for row in st.session_state["draft_high_tier_recipe_rows"]:
                new_row = dict(row)
                new_row[batch_target] = batch_value
                updated_rows.append(new_row)
            st.session_state["draft_high_tier_recipe_rows"] = updated_rows
            st.success(f"已将“{batch_target}”统一设置为 {batch_value}")

    recipe_df = pd.DataFrame(st.session_state["draft_high_tier_recipe_rows"])
    recipe_editor_key = "page3_recipe_editor"
    edited_recipe_df = st.data_editor(
        recipe_df,
        hide_index=True,
        use_container_width=True,
        disabled=["recipe_id", "丹药名称", "lower_pill_id"],
        column_config={
            "recipe_id": st.column_config.TextColumn("recipe_id"),
            "丹药名称": st.column_config.TextColumn("丹药名称"),
            "lower_pill_id": st.column_config.TextColumn("低阶丹药ID"),
            "低阶丹药数量": st.column_config.NumberColumn("低阶丹药数量", min_value=1, step=1),
            "破境草数量": st.column_config.NumberColumn("破境草数量", min_value=1, step=1),
        },
        key=recipe_editor_key,
    )

    valid_rows = []
    for _, row in edited_recipe_df.iterrows():
        valid_rows.append(
            {
                "recipe_id": str(row["recipe_id"]),
                "丹药名称": str(row["丹药名称"]),
                "lower_pill_id": str(row["lower_pill_id"]),
                "低阶丹药数量": max(1, int(row["低阶丹药数量"])),
                "破境草数量": max(1, int(row["破境草数量"])),
            }
        )
    st.session_state["draft_high_tier_recipe_rows"] = valid_rows

    if st.button("保存 recipes 配置", type="primary"):
        latest_base_recipes = load_json(RECIPES_PATH)
        latest_draft_recipes = _build_draft_recipes(latest_base_recipes, st.session_state["draft_high_tier_recipe_rows"])
        save_json(RECIPES_PATH, latest_draft_recipes)
        st.success(f"已保存：{RECIPES_PATH}")

elif page == "战斗建模可视化":
    st.subheader("参数设置")
    c1, c2, c3 = st.columns(3)
    with c1:
        k_value = float(st.number_input("K", min_value=1.0, value=float(DEFAULT_K_VALUE), step=10.0))
    with c2:
        skill_coef = float(st.number_input("技能系数", min_value=0.1, value=1.0, step=0.1))
    with c3:
        battle_interval_seconds = float(
            st.number_input(
                "场间等待时间（秒）",
                min_value=0.0,
                value=float(DEFAULT_BATTLE_INTERVAL_SECONDS),
                step=0.5,
                format="%.1f",
            )
        )
    seed = FIXED_BATTLE_RANDOM_SEED

    st.caption(
        "口径：仅普通历练区；玩家只取基础属性；不考虑术法；穿透固定为0；"
        "每次死亡前最多模拟30场，最多模拟3次，未死亡部分按剩余血量比例外推；"
        f"随机种子固定为 {FIXED_BATTLE_RANDOM_SEED}。"
    )

    st.subheader("每日区域：破境草洞穴可通关境界")
    base_cave_result = _check_foundation_cave_min_pass(
        realms_data=base_realms_data,
        areas_data=base_areas_data,
        enemies_data=base_enemies_data,
        k_value=k_value,
        skill_coef=skill_coef,
        battle_interval_seconds=battle_interval_seconds,
    )
    draft_cave_result = _check_foundation_cave_min_pass(
        realms_data=draft_realms,
        areas_data=draft_areas,
        enemies_data=draft_enemies,
        k_value=k_value,
        skill_coef=skill_coef,
        battle_interval_seconds=battle_interval_seconds,
    )
    if not draft_cave_result.get("exists", False):
        st.info("未找到每日区域：破境草洞穴。")
    else:
        if not draft_cave_result.get("can_lianqi_max", False):
            fail_text = f'{draft_cave_result.get("lianqi_max_stage", "炼气大圆满")}不能打过破境草洞穴'
            st.markdown(f'<span style="color:#c62828;font-weight:700;">{html.escape(fail_text)}</span>', unsafe_allow_html=True)
        else:
            before_text = (
                base_cave_result.get("min_pass_stage", "")
                if base_cave_result.get("can_lianqi_max", False)
                else f'{base_cave_result.get("lianqi_max_stage", "炼气大圆满")}不能打过'
            )
            after_text = draft_cave_result.get("min_pass_stage", "")
            st.markdown(
                f'最小可通关境界：{_build_compare_html(before_text, after_text)}',
                unsafe_allow_html=True,
            )

    st.subheader("南麓试练塔：筑基1层到金丹大圆满最大可通关层")
    st.caption("规则：逐层检测，每层依次模拟塔配置中的每种敌人；同层只要有一种敌人可通关，即视为可通关。")
    base_tower_df = _build_tower_stage_max_floor_table(
        realms_data=base_realms_data,
        areas_data=base_areas_data,
        enemies_data=base_enemies_data,
        k_value=k_value,
        skill_coef=skill_coef,
        battle_interval_seconds=battle_interval_seconds,
    )
    draft_tower_df = _build_tower_stage_max_floor_table(
        realms_data=draft_realms,
        areas_data=draft_areas,
        enemies_data=draft_enemies,
        k_value=k_value,
        skill_coef=skill_coef,
        battle_interval_seconds=battle_interval_seconds,
    )
    if draft_tower_df.empty:
        st.info("未找到南麓试练塔配置或目标境界数据。")
    else:
        _render_compare_table_html(
            base_tower_df,
            draft_tower_df,
            numeric_columns=["最大可通关层"],
        )

    normal_area_options = _get_normal_area_options(draft_areas)
    if not normal_area_options:
        st.warning("未检测到普通历练区域配置。")
    else:
        st.subheader("自定义组合模拟")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            realm_name = st.selectbox("玩家大境界", options=base_realms_data.get("realm_order", []), key="battle_realm")
        realm_max_level = int(base_realms_data.get("realms", {}).get(realm_name, {}).get("max_level", 1))
        with cc2:
            level = int(st.number_input("玩家层级", min_value=1, max_value=max(1, realm_max_level), value=1, step=1))
        with cc3:
            area_label_to_id = {f"{name} ({area_id})": area_id for area_id, name in normal_area_options}
            selected_label = st.selectbox("普通历练区域", options=list(area_label_to_id.keys()), key="battle_area")
            area_id = area_label_to_id[selected_label]

        base_player_attrs = build_player_attrs_from_realm(base_realms_data, realm_name, level)
        draft_player_attrs = build_player_attrs_from_realm(draft_realms, realm_name, level)
        base_area_cfg = base_areas_data.get("normal_areas", {}).get(area_id, {})
        draft_area_cfg = draft_areas.get("normal_areas", {}).get(area_id, base_area_cfg)
        base_custom_result = simulate_average(
            player_attrs=base_player_attrs,
            area_cfg=base_area_cfg,
            enemies_data=base_enemies_data,
            k_value=k_value,
            skill_coef=skill_coef,
            penetration=0.0,
            trials=DEFAULT_TRIALS,
            max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
            battle_interval_seconds=battle_interval_seconds,
            seed=seed,
        )
        draft_custom_result = simulate_average(
            player_attrs=draft_player_attrs,
            area_cfg=draft_area_cfg,
            enemies_data=draft_enemies,
            k_value=k_value,
            skill_coef=skill_coef,
            penetration=0.0,
            trials=DEFAULT_TRIALS,
            max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
            battle_interval_seconds=battle_interval_seconds,
            seed=seed,
        )

        before_fights_text = "♾️" if base_custom_result.get("infinite_fights", False) else format_number(base_custom_result["avg_fights"])
        after_fights_text = "♾️" if draft_custom_result.get("infinite_fights", False) else format_number(draft_custom_result["avg_fights"])
        before_spirit_per_hour = float(base_custom_result["avg_item_per_hour"].get("spirit_stone", 0.0))
        after_spirit_per_hour = float(draft_custom_result["avg_item_per_hour"].get("spirit_stone", 0.0))
        _render_compare_metrics(
            [
                {"label": "平均战斗次数", "value_html": _build_compare_html(before_fights_text, after_fights_text)},
                {
                    "label": "平均战斗效率(次/小时)",
                    "value_html": _build_compare_number_html(base_custom_result["avg_fights_per_hour"], draft_custom_result["avg_fights_per_hour"]),
                },
                {
                    "label": "灵石掉落数量(每小时)",
                    "value_html": _build_compare_number_html(before_spirit_per_hour, after_spirit_per_hour),
                },
            ]
        )

        st.subheader("批量矩阵（炼气/筑基/金丹 的 1层和5层 × 普通区域）")
        before_matrix_df, before_reward_matrix_df = _build_battle_matrix(
            realms_data=base_realms_data,
            areas_data=base_areas_data,
            enemies_data=base_enemies_data,
            k_value=k_value,
            skill_coef=skill_coef,
            trials=DEFAULT_TRIALS,
            max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
            battle_interval_seconds=battle_interval_seconds,
            seed=seed,
        )
        after_matrix_df, after_reward_matrix_df = _build_battle_matrix(
            realms_data=draft_realms,
            areas_data=draft_areas,
            enemies_data=draft_enemies,
            k_value=k_value,
            skill_coef=skill_coef,
            trials=DEFAULT_TRIALS,
            max_fights_per_trial=DEFAULT_MAX_FIGHTS_PER_TRIAL,
            battle_interval_seconds=battle_interval_seconds,
            seed=seed,
        )

        if not after_matrix_df.empty:
            before_reward_map: dict[tuple[str, int, str], dict[str, float]] = {}
            if not before_reward_matrix_df.empty:
                grouped = before_reward_matrix_df.groupby(["realm_name", "level", "area_id", "area_name"], as_index=False)
                for _, group in grouped:
                    reward_items = {str(row["item_id"]): float(row["avg_per_hour"]) for _, row in group.iterrows()}
                    before_reward_map[
                        (str(group.iloc[0]["realm_name"]), int(group.iloc[0]["level"]), str(group.iloc[0]["area_id"]))
                    ] = reward_items

            after_reward_map: dict[tuple[str, int, str], dict[str, float]] = {}
            if not after_reward_matrix_df.empty:
                grouped = after_reward_matrix_df.groupby(["realm_name", "level", "area_id", "area_name"], as_index=False)
                for _, group in grouped:
                    reward_items = {str(row["item_id"]): float(row["avg_per_hour"]) for _, row in group.iterrows()}
                    after_reward_map[
                        (str(group.iloc[0]["realm_name"]), int(group.iloc[0]["level"]), str(group.iloc[0]["area_id"]))
                    ] = reward_items

            before_stage_max_spirit: dict[str, float] = {}
            for _, row in before_matrix_df.iterrows():
                key = (str(row["realm_name"]), int(row["level"]), str(row["area_id"]))
                stage = f'{row["realm_name"]}{int(row["level"])}层'
                spirit_value = float(before_reward_map.get(key, {}).get("spirit_stone", 0.0))
                before_stage_max_spirit[stage] = max(before_stage_max_spirit.get(stage, 0.0), spirit_value)

            after_stage_max_spirit: dict[str, float] = {}
            for _, row in after_matrix_df.iterrows():
                key = (str(row["realm_name"]), int(row["level"]), str(row["area_id"]))
                stage = f'{row["realm_name"]}{int(row["level"])}层'
                spirit_value = float(after_reward_map.get(key, {}).get("spirit_stone", 0.0))
                after_stage_max_spirit[stage] = max(after_stage_max_spirit.get(stage, 0.0), spirit_value)

            before_matrix_rows = []
            for _, row in before_matrix_df.iterrows():
                key = (str(row["realm_name"]), int(row["level"]), str(row["area_id"]))
                stage = f'{row["realm_name"]}{int(row["level"])}层'
                avg_fights_value = float(row["avg_fights"])
                avg_fights_display = "♾️" if bool(row.get("infinite_fights", False)) else format_number(avg_fights_value)
                reward_items = before_reward_map.get(key, {})
                spirit_cell, others_cell = _split_reward_cells(reward_items, item_name_map)
                if avg_fights_value <= 0.0:
                    spirit_cell = ""
                    others_cell = ""
                before_matrix_rows.append(
                    {
                        "stage": stage,
                        "max_spirit": format_number(before_stage_max_spirit.get(stage, 0.0)),
                        "area": str(row["area_name"]),
                        "avg_fights": avg_fights_display,
                        "efficiency": format_number(float(row["avg_fights_per_hour"])),
                        "spirit": spirit_cell,
                        "others": others_cell,
                    }
                )

            after_matrix_rows = []
            for _, row in after_matrix_df.iterrows():
                key = (str(row["realm_name"]), int(row["level"]), str(row["area_id"]))
                stage = f'{row["realm_name"]}{int(row["level"])}层'
                avg_fights_value = float(row["avg_fights"])
                avg_fights_display = "♾️" if bool(row.get("infinite_fights", False)) else format_number(avg_fights_value)
                reward_items = after_reward_map.get(key, {})
                spirit_cell, others_cell = _split_reward_cells(reward_items, item_name_map)
                if avg_fights_value <= 0.0:
                    spirit_cell = ""
                    others_cell = ""
                after_matrix_rows.append(
                    {
                        "stage": stage,
                        "max_spirit": format_number(after_stage_max_spirit.get(stage, 0.0)),
                        "area": str(row["area_name"]),
                        "avg_fights": avg_fights_display,
                        "efficiency": format_number(float(row["avg_fights_per_hour"])),
                        "spirit": spirit_cell,
                        "others": others_cell,
                    }
                )
            _render_battle_matrix_compare_html(before_matrix_rows, after_matrix_rows)
