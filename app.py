from copy import deepcopy
import json

import pandas as pd
import streamlit as st

from src.io.data_paths import REALMS_PATH, RECIPES_PATH
from src.io.data_sync import ensure_local_data
from src.io.json_store import load_json, save_json
from src.io.realms_text_updater import save_realms_numeric_fields_preserve_format
from src.model.formatting import format_number
from src.model.realm_generator import apply_generation_rules
from src.model.time_model import build_time_rows


st.set_page_config(page_title="境界数值模型", layout="wide")
st.title("境界数值模型（一期）")
st.caption("目标：评估玩家从炼气一层到最高层的修炼耗时合理性。")


def _load_data():
    ensure_local_data()
    return load_json(REALMS_PATH), load_json(RECIPES_PATH)


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

    z1_cost = float(zhuji_levels["1"]["spirit_energy_cost"])
    z2_cost = float(zhuji_levels["2"]["spirit_energy_cost"])
    j1_cost = float(jindan_levels["1"]["spirit_energy_cost"])

    z1_max = float(zhuji_levels["1"]["max_spirit_energy"])
    z2_max = float(zhuji_levels["2"]["max_spirit_energy"])
    j1_max = float(jindan_levels["1"]["max_spirit_energy"])

    level_multiplier = _safe_ratio(z2_cost, z1_cost, 1.10)
    if level_multiplier <= 1.0:
        level_multiplier = _safe_ratio(z2_max, z1_max, 1.10)

    realm_multiplier = _safe_ratio(j1_cost, z1_cost, 5.00)
    if realm_multiplier <= 1.0:
        realm_multiplier = _safe_ratio(j1_max, z1_max, 5.00)

    return {
        "foundation_base_cost": int(z1_cost),
        "foundation_base_max_spirit": int(z1_max),
        "level_multiplier": float(f"{level_multiplier:.2f}"),
        "realm_multiplier": float(f"{realm_multiplier:.2f}"),
    }


def _get_lianqi_editor_df(realms_data: dict) -> pd.DataFrame:
    lianqi_levels = realms_data["realms"]["炼气期"]["levels"]
    rows = []
    for level in sorted(lianqi_levels.keys(), key=int):
        info = lianqi_levels[level]
        rows.append(
            {
                "层级": int(level),
                "spirit_energy_cost": int(info["spirit_energy_cost"]),
                "max_spirit_energy": int(info["max_spirit_energy"]),
            }
        )
    return pd.DataFrame(rows)


def _extract_lianqi_values(df: pd.DataFrame):
    costs = {}
    max_spirits = {}
    for _, row in df.iterrows():
        level = int(row["层级"])
        costs[level] = int(row["spirit_energy_cost"])
        max_spirits[level] = int(row["max_spirit_energy"])
    return costs, max_spirits


def _prepare_display_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in [
        "step_spirit_hours",
        "step_material_hours",
        "cumulative_spirit_days",
        "cumulative_material_days",
    ]:
        df[col + "_display"] = df[col].map(format_number)
    return df


def _init_realm_draft_state(realms_data: dict):
    signature = _realms_signature(realms_data)
    prev_signature = st.session_state.get("realm_source_signature", "")
    should_reset = prev_signature != signature

    defaults = _derive_default_params(realms_data)
    if "draft_foundation_base_cost" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_cost"] = defaults["foundation_base_cost"]
    if "draft_foundation_base_max_spirit" not in st.session_state or should_reset:
        st.session_state["draft_foundation_base_max_spirit"] = defaults["foundation_base_max_spirit"]
    if "draft_level_multiplier" not in st.session_state or should_reset:
        st.session_state["draft_level_multiplier"] = defaults["level_multiplier"]
    if "draft_realm_multiplier" not in st.session_state or should_reset:
        st.session_state["draft_realm_multiplier"] = defaults["realm_multiplier"]
    if "draft_lianqi_rows" not in st.session_state or should_reset:
        st.session_state["draft_lianqi_rows"] = _get_lianqi_editor_df(realms_data).to_dict("records")
    # 兼容旧会话脏状态：若四个参数都回落到 1/1.00，则按配置重置。
    if (
        int(st.session_state.get("draft_foundation_base_cost", 1)) == 1
        and int(st.session_state.get("draft_foundation_base_max_spirit", 1)) == 1
        and float(st.session_state.get("draft_level_multiplier", 1.0)) == 1.0
        and float(st.session_state.get("draft_realm_multiplier", 1.0)) == 1.0
    ):
        st.session_state["draft_foundation_base_cost"] = defaults["foundation_base_cost"]
        st.session_state["draft_foundation_base_max_spirit"] = defaults["foundation_base_max_spirit"]
        st.session_state["draft_level_multiplier"] = defaults["level_multiplier"]
        st.session_state["draft_realm_multiplier"] = defaults["realm_multiplier"]
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
    lianqi_costs, lianqi_max_spirits = _extract_lianqi_values(lianqi_df)
    return apply_generation_rules(
        realms_data=deepcopy(base_realms),
        lianqi_costs=lianqi_costs,
        lianqi_max_spirits=lianqi_max_spirits,
        foundation_base_cost=int(st.session_state["draft_foundation_base_cost"]),
        foundation_base_max_spirit=int(st.session_state["draft_foundation_base_max_spirit"]),
        level_multiplier=float(st.session_state["draft_level_multiplier"]),
        realm_multiplier=float(st.session_state["draft_realm_multiplier"]),
    )


def _render_summary(df: pd.DataFrame):
    if df.empty:
        return
    spirit_total = float(df["cumulative_spirit_days"].iloc[-1])
    material_total = float(df["cumulative_material_days"].iloc[-1])
    c1, c2 = st.columns(2)
    c1.metric("总灵气耗时（天）", format_number(spirit_total))
    c2.metric("总材料耗时（天）", format_number(material_total))

def _build_realm_max_summary(df: pd.DataFrame, realm_order: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby("realm_name", as_index=False)
        .agg(
            realm_spirit_days=("step_spirit_hours", lambda x: float(x.sum()) / 24.0),
            realm_material_days=("step_material_hours", lambda x: float(x.sum()) / 24.0),
        )
    )
    grouped["realm_max_days"] = grouped[["realm_spirit_days", "realm_material_days"]].max(axis=1)
    grouped["realm_spirit_days_display"] = grouped["realm_spirit_days"].map(format_number)
    grouped["realm_material_days_display"] = grouped["realm_material_days"].map(format_number)
    grouped["realm_max_days_display"] = grouped["realm_max_days"].map(format_number)
    order_rank = {name: i for i, name in enumerate(realm_order)}
    grouped["order_rank"] = grouped["realm_name"].map(lambda x: order_rank.get(x, 999))
    grouped = grouped.sort_values("order_rank").reset_index(drop=True)
    return grouped

base_realms_data, base_recipes_data = _load_data()
_init_realm_draft_state(base_realms_data)
_init_recipe_draft_state(base_recipes_data)

draft_realms = _build_draft_realms(base_realms_data)
draft_recipes = _build_draft_recipes(base_recipes_data, st.session_state["draft_high_tier_recipe_rows"])
display_df = _prepare_display_df(build_time_rows(draft_realms, draft_recipes))

with st.sidebar:
    page = st.radio(
        "页面导航",
        ["首页（可视化分析）", "境界配置（realms）", "丹方配置（recipes）"],
        index=0,
    )

if page == "首页（可视化分析）":
    st.caption("当前页面展示的是“草稿预览效果”，包含未保存到文件的配置改动。")
    _render_summary(display_df)

    st.subheader("升级明细（层间：小时；累计：天）")
    table_df = display_df[
        [
            "step_index",
            "from_stage",
            "to_stage",
            "spirit_energy_cost",
            "foundation_herb_needed",
            "step_spirit_hours_display",
            "step_material_hours_display",
            "cumulative_spirit_days_display",
            "cumulative_material_days_display",
        ]
    ].rename(
        columns={
            "step_index": "序号",
            "from_stage": "从",
            "to_stage": "到",
            "spirit_energy_cost": "灵气消耗",
            "foundation_herb_needed": "破境草需求",
            "step_spirit_hours_display": "层间灵气耗时(小时)",
            "step_material_hours_display": "层间材料耗时(小时)",
            "cumulative_spirit_days_display": "累计灵气耗时(天)",
            "cumulative_material_days_display": "累计材料耗时(天)",
        }
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    st.subheader("大境界耗时汇总（Max）")
    realm_summary_df = _build_realm_max_summary(display_df, draft_realms["realm_order"])
    if not realm_summary_df.empty:
        st.dataframe(
            realm_summary_df[
                ["realm_name", "realm_spirit_days_display", "realm_material_days_display", "realm_max_days_display"]
            ].rename(
                columns={
                    "realm_name": "大境界",
                    "realm_spirit_days_display": "该境界灵气总耗时(天)",
                    "realm_material_days_display": "该境界材料总耗时(天)",
                    "realm_max_days_display": "该境界Max耗时(天)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

elif page == "境界配置（realms）":
    st.subheader("生成参数（realms.json 相关）")
    page2_base_cost = int(
        st.number_input(
        "筑基1层 spirit_energy_cost 基准",
        min_value=1,
        value=int(st.session_state.get("draft_foundation_base_cost", 1)),
        step=1,
        key="page2_foundation_base_cost",
        )
    )
    st.session_state["draft_foundation_base_cost"] = page2_base_cost

    page2_base_max = int(
        st.number_input(
        "筑基1层 max_spirit_energy 基准",
        min_value=1,
        value=int(st.session_state.get("draft_foundation_base_max_spirit", 1)),
        step=1,
        key="page2_foundation_base_max_spirit",
        )
    )
    st.session_state["draft_foundation_base_max_spirit"] = page2_base_max

    page2_level_mult = float(
        st.number_input(
        "层内递推倍率",
        min_value=1.00,
        value=float(st.session_state.get("draft_level_multiplier", 1.0)),
        step=0.01,
        format="%.2f",
        key="page2_level_multiplier",
        )
    )
    st.session_state["draft_level_multiplier"] = page2_level_mult

    page2_realm_mult = float(
        st.number_input(
        "跨大境界首层倍率",
        min_value=1.00,
        value=float(st.session_state.get("draft_realm_multiplier", 1.0)),
        step=0.10,
        format="%.2f",
        key="page2_realm_multiplier",
        )
    )
    st.session_state["draft_realm_multiplier"] = page2_realm_mult
    st.caption("材料获取速率固定：foundation_herb = 30 / 天")

    st.subheader("炼气期手动编辑（保留手动值）")
    edited_lianqi_df = st.data_editor(
        pd.DataFrame(st.session_state["draft_lianqi_rows"]),
        hide_index=True,
        use_container_width=True,
        disabled=["层级"],
        key="page2_lianqi_editor",
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
        key="page3_recipe_editor",
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
