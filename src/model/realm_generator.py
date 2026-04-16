from copy import deepcopy
from typing import Dict


LIANQI_REALM = "炼气期"
FOUNDATION_REALM = "筑基期"


def apply_generation_rules(
    realms_data: Dict,
    lianqi_healths: Dict[int, int],
    lianqi_attacks: Dict[int, int],
    lianqi_defenses: Dict[int, int],
    lianqi_costs: Dict[int, int],
    lianqi_stone_costs: Dict[int, int],
    lianqi_max_spirits: Dict[int, int],
    foundation_base_health: int,
    foundation_base_attack: int,
    foundation_base_defense: int,
    foundation_base_cost: int,
    foundation_base_stone_cost: int,
    foundation_base_max_spirit: int,
    resource_level_multiplier: float,
    resource_realm_multiplier: float,
    stat_level_multiplier: float,
    stat_realm_multiplier: float,
) -> Dict:
    result = deepcopy(realms_data)
    realms = result["realms"]
    realm_order = result["realm_order"]

    _apply_lianqi_manual(
        realm=realms[LIANQI_REALM],
        healths=lianqi_healths,
        attacks=lianqi_attacks,
        defenses=lianqi_defenses,
        costs=lianqi_costs,
        stone_costs=lianqi_stone_costs,
        max_spirits=lianqi_max_spirits,
    )

    if FOUNDATION_REALM not in realm_order:
        raise ValueError("realm_order missing 筑基期")

    start_idx = realm_order.index(FOUNDATION_REALM)
    health_realm_first = int(foundation_base_health)
    attack_realm_first = int(foundation_base_attack)
    defense_realm_first = int(foundation_base_defense)
    cost_realm_first = int(foundation_base_cost)
    stone_cost_realm_first = int(foundation_base_stone_cost)
    max_realm_first = int(foundation_base_max_spirit)

    for realm_name in realm_order[start_idx:]:
        levels = realms[realm_name]["levels"]
        _apply_single_realm(levels, first_value=health_realm_first, field="health", level_multiplier=stat_level_multiplier)
        _apply_single_realm(levels, first_value=attack_realm_first, field="attack", level_multiplier=stat_level_multiplier)
        _apply_single_realm(levels, first_value=defense_realm_first, field="defense", level_multiplier=stat_level_multiplier)
        _apply_single_realm(levels, first_value=cost_realm_first, field="spirit_energy_cost", level_multiplier=resource_level_multiplier)
        _apply_single_realm(levels, first_value=stone_cost_realm_first, field="spirit_stone_cost", level_multiplier=resource_level_multiplier)
        _apply_single_realm(levels, first_value=max_realm_first, field="max_spirit_energy", level_multiplier=resource_level_multiplier)
        health_realm_first = int(health_realm_first * stat_realm_multiplier)
        attack_realm_first = int(attack_realm_first * stat_realm_multiplier)
        defense_realm_first = int(defense_realm_first * stat_realm_multiplier)
        cost_realm_first = int(cost_realm_first * resource_realm_multiplier)
        stone_cost_realm_first = int(stone_cost_realm_first * resource_realm_multiplier)
        max_realm_first = int(max_realm_first * resource_realm_multiplier)

    return result


def _apply_lianqi_manual(
    realm: Dict,
    healths: Dict[int, int],
    attacks: Dict[int, int],
    defenses: Dict[int, int],
    costs: Dict[int, int],
    stone_costs: Dict[int, int],
    max_spirits: Dict[int, int],
) -> None:
    levels = realm["levels"]
    for level_str in sorted(levels.keys(), key=int):
        level_int = int(level_str)
        if level_int in healths:
            levels[level_str]["health"] = int(healths[level_int])
        if level_int in attacks:
            levels[level_str]["attack"] = int(attacks[level_int])
        if level_int in defenses:
            levels[level_str]["defense"] = int(defenses[level_int])
        if level_int in costs:
            levels[level_str]["spirit_energy_cost"] = int(costs[level_int])
        if level_int in stone_costs:
            levels[level_str]["spirit_stone_cost"] = int(stone_costs[level_int])
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
