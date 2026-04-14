from typing import Dict, List

from src.model.material_model import calc_foundation_herb_needed, get_breakthrough_materials_for_step


FOUNDATION_HERB_PER_DAY = 30


def build_time_rows(realms_data: Dict, recipes_data: Dict) -> List[Dict]:
    rows: List[Dict] = []
    cumulative_spirit_days = 0.0
    cumulative_material_days = 0.0
    step_index = 0

    for realm_name in realms_data["realm_order"]:
        realm = realms_data["realms"][realm_name]
        max_level = int(realm["max_level"])
        spirit_gain_speed = float(realm["spirit_gain_speed"])

        for level in range(1, max_level + 1):
            next_target = _build_next_target(realm_name, level, max_level, realm.get("next_realm", ""))
            if not next_target:
                continue

            level_data = realm["levels"][str(level)]
            spirit_cost = float(level_data["spirit_energy_cost"])
            step_spirit_hours = spirit_cost / spirit_gain_speed / 3600.0 if spirit_gain_speed > 0 else 0.0

            materials = get_breakthrough_materials_for_step(realms_data, realm_name, level)
            herb_needed = calc_foundation_herb_needed(materials, recipes_data)
            step_material_days = float(herb_needed) / float(FOUNDATION_HERB_PER_DAY)
            step_material_hours = step_material_days * 24.0

            cumulative_spirit_days += step_spirit_hours / 24.0
            cumulative_material_days += step_material_days

            step_index += 1
            rows.append(
                {
                    "step_index": step_index,
                    "realm_name": realm_name,
                    "from_stage": f"{realm_name}{_level_name(realm, level)}",
                    "to_stage": next_target,
                    "spirit_gain_speed": spirit_gain_speed,
                    "spirit_energy_cost": int(spirit_cost),
                    "foundation_herb_needed": herb_needed,
                    "step_spirit_hours": step_spirit_hours,
                    "step_material_hours": step_material_hours,
                    "cumulative_spirit_days": cumulative_spirit_days,
                    "cumulative_material_days": cumulative_material_days,
                }
            )

    return rows


def _build_next_target(realm_name: str, level: int, max_level: int, next_realm: str) -> str:
    if level < max_level:
        return f"{realm_name}第{level + 1}层"
    if next_realm:
        return f"{next_realm}第1层"
    return ""


def _level_name(realm: Dict, level: int) -> str:
    names = realm.get("level_names", {})
    return str(names.get(str(level), f"第{level}层"))
