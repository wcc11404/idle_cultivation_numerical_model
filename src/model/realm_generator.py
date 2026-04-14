from copy import deepcopy
from typing import Dict


LIANQI_REALM = "炼气期"
FOUNDATION_REALM = "筑基期"


def apply_generation_rules(
    realms_data: Dict,
    lianqi_costs: Dict[int, int],
    lianqi_max_spirits: Dict[int, int],
    foundation_base_cost: int,
    foundation_base_max_spirit: int,
    level_multiplier: float,
    realm_multiplier: float,
) -> Dict:
    result = deepcopy(realms_data)
    realms = result["realms"]
    realm_order = result["realm_order"]

    _apply_lianqi_manual(realm=realms[LIANQI_REALM], costs=lianqi_costs, max_spirits=lianqi_max_spirits)

    if FOUNDATION_REALM not in realm_order:
        raise ValueError("realm_order missing 筑基期")

    start_idx = realm_order.index(FOUNDATION_REALM)
    cost_realm_first = int(foundation_base_cost)
    max_realm_first = int(foundation_base_max_spirit)

    for realm_name in realm_order[start_idx:]:
        levels = realms[realm_name]["levels"]
        _apply_single_realm(levels, first_value=cost_realm_first, field="spirit_energy_cost", level_multiplier=level_multiplier)
        _apply_single_realm(levels, first_value=max_realm_first, field="max_spirit_energy", level_multiplier=level_multiplier)
        cost_realm_first = int(cost_realm_first * realm_multiplier)
        max_realm_first = int(max_realm_first * realm_multiplier)

    return result


def _apply_lianqi_manual(realm: Dict, costs: Dict[int, int], max_spirits: Dict[int, int]) -> None:
    levels = realm["levels"]
    for level_str in sorted(levels.keys(), key=int):
        level_int = int(level_str)
        if level_int in costs:
            levels[level_str]["spirit_energy_cost"] = int(costs[level_int])
        if level_int in max_spirits:
            levels[level_str]["max_spirit_energy"] = int(max_spirits[level_int])


def _apply_single_realm(levels: Dict, first_value: int, field: str, level_multiplier: float) -> None:
    ordered_levels = sorted(levels.keys(), key=int)
    current_value = int(first_value)
    for i, level_str in enumerate(ordered_levels):
        if i == 0:
            value = current_value
        else:
            value = int(current_value * level_multiplier)
            current_value = value
        levels[level_str][field] = int(value)
