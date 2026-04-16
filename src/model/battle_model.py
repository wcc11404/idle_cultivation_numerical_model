from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Dict, Optional


ATB_MAX = 100.0
TICK_INTERVAL = 0.1
DEATH_RECOVER_SECONDS = 100.0
DEFAULT_TRIALS = 3
DEFAULT_MAX_FIGHTS_PER_TRIAL = 30
DEFAULT_BATTLE_INTERVAL_SECONDS = 4.0
FIXED_BATTLE_RANDOM_SEED = 20260416
MIN_TOTAL_SIMULATED_BATTLES = 11
MAX_DYNAMIC_TRIALS = 30


def calculate_damage(
    attack: float,
    defense: float,
    penetration: float,
    k_value: float,
    skill_coef: float,
) -> float:
    effective_defense = max(defense - penetration, 0.0)
    defense_ratio = effective_defense / max(effective_defense + k_value, k_value)
    base_damage = max(attack * (1.0 - defense_ratio), 1.0)
    return round(base_damage * skill_coef, 2)


def generate_enemy_for_area(area_cfg: Dict[str, Any], enemies_data: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    templates = area_cfg.get("enemies_template", [])
    if not templates:
        return {}

    weights = [int(max(0, t.get("weight", 0))) for t in templates]
    if sum(weights) <= 0:
        selected = templates[0]
    else:
        selected = rng.choices(templates, weights=weights, k=1)[0]

    enemies = selected.get("enemies", [])
    if not enemies:
        return {}
    enemy_desc = enemies[0]

    template_id = str(enemy_desc.get("template", ""))
    min_level = int(enemy_desc.get("min_level", 1))
    max_level = int(enemy_desc.get("max_level", min_level))
    if max_level < min_level:
        max_level = min_level
    level = rng.randint(min_level, max_level)

    templates_cfg = enemies_data.get("templates", {})
    template_cfg = templates_cfg.get(template_id, {})
    growth = template_cfg.get("growth", {})

    health = int(growth.get("health_base", 20) * math.pow(growth.get("health_growth", 1.08), level - 1))
    attack = int(growth.get("attack_base", 4) * math.pow(growth.get("attack_growth", 1.06), level - 1))
    defense = int(growth.get("defense_base", 2) * math.pow(growth.get("defense_growth", 1.04), level - 1))
    speed = float(growth.get("speed_base", 5.0)) * (1.0 + float(growth.get("speed_growth", 0.01)) * float(level - 1))

    return {
        "template_id": template_id,
        "level": level,
        "health": float(health),
        "max_health": float(health),
        "attack": float(attack),
        "defense": float(defense),
        "speed": float(speed),
        "drops": selected.get("drops", {}),
    }


def _roll_drops(drops_cfg: Dict[str, Any], rng: random.Random) -> Dict[str, int]:
    drops: Dict[str, int] = {}
    for item_id, info in drops_cfg.items():
        chance = float(info.get("chance", 1.0))
        if rng.random() > chance:
            continue
        min_amount = int(info.get("min", 0))
        max_amount = int(info.get("max", min_amount))
        if max_amount < min_amount:
            max_amount = min_amount
        amount = rng.randint(min_amount, max_amount)
        if amount > 0:
            drops[str(item_id)] = drops.get(str(item_id), 0) + amount
    return drops


def _calculate_expected_drops_per_fight(area_cfg: Dict[str, Any]) -> Dict[str, float]:
    templates = area_cfg.get("enemies_template", [])
    if not templates:
        return {}

    weights = [float(max(0, t.get("weight", 0))) for t in templates]
    weight_sum = sum(weights)
    if weight_sum <= 0.0:
        template_probs = [1.0 if i == 0 else 0.0 for i in range(len(templates))]
    else:
        template_probs = [w / weight_sum for w in weights]

    expected: Dict[str, float] = defaultdict(float)
    for idx, template in enumerate(templates):
        p_template = template_probs[idx]
        if p_template <= 0.0:
            continue
        drops_cfg = template.get("drops", {})
        for item_id, info in drops_cfg.items():
            chance = float(info.get("chance", 1.0))
            min_amount = int(info.get("min", 0))
            max_amount = int(info.get("max", min_amount))
            if max_amount < min_amount:
                max_amount = min_amount
            expected_amount_if_drop = (float(min_amount) + float(max_amount)) / 2.0
            expected[str(item_id)] += p_template * chance * expected_amount_if_drop
    return dict(expected)


def _simulate_single_battle(
    player_attack: float,
    player_defense: float,
    player_speed: float,
    player_health_start: float,
    enemy: Dict[str, Any],
    k_value: float,
    skill_coef: float,
    penetration: float,
    max_ticks: int = 200000,
) -> Dict[str, Any]:
    player_health = float(player_health_start)
    enemy_health = float(enemy.get("health", 0.0))

    player_atb = 0.0
    enemy_atb = 0.0
    current_time = 0.0
    ticks = 0

    while player_health > 0.0 and enemy_health > 0.0 and ticks < max_ticks:
        ticks += 1
        current_time += TICK_INTERVAL

        player_atb += player_speed
        enemy_atb += float(enemy.get("speed", 0.0))

        player_ready = player_atb >= ATB_MAX
        enemy_ready = enemy_atb >= ATB_MAX

        if player_ready and enemy_ready:
            if player_speed > float(enemy.get("speed", 0.0)):
                damage = calculate_damage(
                    attack=player_attack,
                    defense=float(enemy.get("defense", 0.0)),
                    penetration=penetration,
                    k_value=k_value,
                    skill_coef=skill_coef,
                )
                enemy_health = round(max(0.0, enemy_health - damage), 2)
                player_atb -= ATB_MAX
                if enemy_health <= 0.0:
                    break

                damage = calculate_damage(
                    attack=float(enemy.get("attack", 0.0)),
                    defense=player_defense,
                    penetration=penetration,
                    k_value=k_value,
                    skill_coef=skill_coef,
                )
                player_health = round(max(0.0, player_health - damage), 2)
                enemy_atb -= ATB_MAX
            else:
                damage = calculate_damage(
                    attack=float(enemy.get("attack", 0.0)),
                    defense=player_defense,
                    penetration=penetration,
                    k_value=k_value,
                    skill_coef=skill_coef,
                )
                player_health = round(max(0.0, player_health - damage), 2)
                enemy_atb -= ATB_MAX
                if player_health <= 0.0:
                    break

                damage = calculate_damage(
                    attack=player_attack,
                    defense=float(enemy.get("defense", 0.0)),
                    penetration=penetration,
                    k_value=k_value,
                    skill_coef=skill_coef,
                )
                enemy_health = round(max(0.0, enemy_health - damage), 2)
                player_atb -= ATB_MAX
        elif player_ready:
            damage = calculate_damage(
                attack=player_attack,
                defense=float(enemy.get("defense", 0.0)),
                penetration=penetration,
                k_value=k_value,
                skill_coef=skill_coef,
            )
            enemy_health = round(max(0.0, enemy_health - damage), 2)
            player_atb -= ATB_MAX
        elif enemy_ready:
            damage = calculate_damage(
                attack=float(enemy.get("attack", 0.0)),
                defense=player_defense,
                penetration=penetration,
                k_value=k_value,
                skill_coef=skill_coef,
            )
            player_health = round(max(0.0, player_health - damage), 2)
            enemy_atb -= ATB_MAX

    return {
        "victory": enemy_health <= 0.0 and player_health > 0.0,
        "timed_out": ticks >= max_ticks and player_health > 0.0 and enemy_health > 0.0,
        "total_time_seconds": round(current_time, 2),
        "player_health_after": player_health,
    }


def simulate_trial(
    player_attrs: Dict[str, float],
    area_cfg: Dict[str, Any],
    enemies_data: Dict[str, Any],
    *,
    k_value: float,
    skill_coef: float,
    penetration: float = 0.0,
    max_fights_per_trial: int = 1000,
    battle_interval_seconds: float = DEFAULT_BATTLE_INTERVAL_SECONDS,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    health = float(player_attrs["health"])
    attack = float(player_attrs["attack"])
    defense = float(player_attrs["defense"])
    speed = float(player_attrs["speed"])

    total_time_seconds = 0.0
    victory_count = 0
    simulated_battle_count = 0
    drops: Dict[str, int] = defaultdict(int)
    timed_out = False

    start_health = float(player_attrs["health"])

    battle_interval_seconds = max(0.0, float(battle_interval_seconds))

    while health > 0.0 and victory_count < max_fights_per_trial:
        if victory_count > 0 and battle_interval_seconds > 0.0:
            total_time_seconds += battle_interval_seconds

        enemy = generate_enemy_for_area(area_cfg, enemies_data, rng)
        if not enemy:
            break
        simulated_battle_count += 1
        battle_result = _simulate_single_battle(
            player_attack=attack,
            player_defense=defense,
            player_speed=speed,
            player_health_start=health,
            enemy=enemy,
            k_value=k_value,
            skill_coef=skill_coef,
            penetration=penetration,
        )
        total_time_seconds += float(battle_result["total_time_seconds"])
        health = float(battle_result["player_health_after"])
        timed_out = timed_out or bool(battle_result["timed_out"])

        if battle_result["victory"]:
            victory_count += 1
            round_drops = _roll_drops(enemy.get("drops", {}), rng)
            for item_id, amount in round_drops.items():
                drops[item_id] += int(amount)
        else:
            break

    total_hours = total_time_seconds / 3600.0 if total_time_seconds > 0.0 else 0.0
    item_per_hour: Dict[str, float] = {}
    for item_id, amount in drops.items():
        item_per_hour[item_id] = (amount / total_hours) if total_hours > 0.0 else 0.0

    return {
        "start_health": start_health,
        "end_health": health,
        "victory_count": victory_count,
        "simulated_battle_count": simulated_battle_count,
        "total_time_seconds": total_time_seconds,
        "total_time_hours": total_hours,
        "drops": dict(drops),
        "item_per_hour": item_per_hour,
        "capped": health > 0.0 and victory_count >= max_fights_per_trial,
        "no_health_loss_when_capped": (health > 0.0 and victory_count >= max_fights_per_trial and (start_health - health) <= 0.0),
        "timed_out": timed_out,
    }


def simulate_average(
    player_attrs: Dict[str, float],
    area_cfg: Dict[str, Any],
    enemies_data: Dict[str, Any],
    *,
    k_value: float,
    skill_coef: float,
    penetration: float = 0.0,
    trials: int = DEFAULT_TRIALS,
    max_fights_per_trial: int = DEFAULT_MAX_FIGHTS_PER_TRIAL,
    battle_interval_seconds: float = DEFAULT_BATTLE_INTERVAL_SECONDS,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    if trials <= 0:
        trials = DEFAULT_TRIALS
    if max_fights_per_trial <= 0:
        max_fights_per_trial = DEFAULT_MAX_FIGHTS_PER_TRIAL
    battle_interval_seconds = max(0.0, float(battle_interval_seconds))

    total_estimated_fights = 0.0
    total_estimated_hours = 0.0
    capped_count = 0
    timed_out_count = 0
    infinite_trial_count = 0
    total_simulated_hours_for_infinite = 0.0
    total_simulated_fights_for_infinite = 0.0
    total_simulated_battles = 0
    executed_trials = 0
    opening_death = False

    i = 0
    while True:
        trial_seed = None if seed is None else seed + i
        result = simulate_trial(
            player_attrs=player_attrs,
            area_cfg=area_cfg,
            enemies_data=enemies_data,
            k_value=k_value,
            skill_coef=skill_coef,
            penetration=penetration,
            max_fights_per_trial=max_fights_per_trial,
            battle_interval_seconds=battle_interval_seconds,
            seed=trial_seed,
        )
        executed_trials += 1

        simulated_fights = float(result["victory_count"])
        simulated_hours = float(result["total_time_hours"])
        simulated_battles = int(result.get("simulated_battle_count", 0))
        total_simulated_battles += simulated_battles
        trial_capped = bool(result["capped"])
        trial_timed_out = bool(result["timed_out"])
        trial_infinite = bool(result.get("no_health_loss_when_capped", False) and trial_capped)

        # 规则：单次最多模拟30场；若30场后仍存活，则按扣血比例外推本次总场次与总耗时。
        estimated_fights = simulated_fights
        estimated_hours = simulated_hours
        if trial_infinite:
            infinite_trial_count += 1
            total_simulated_hours_for_infinite += simulated_hours
            total_simulated_fights_for_infinite += simulated_fights
        elif trial_capped and float(result["end_health"]) > 0.0 and float(result["start_health"]) > 0.0:
            consumed = float(result["start_health"] - result["end_health"])
            if consumed > 0.0:
                health_ratio = float(result["start_health"]) / consumed
                estimated_fights = simulated_fights * health_ratio
                estimated_hours = simulated_hours * health_ratio

        total_estimated_fights += estimated_fights
        total_estimated_hours += estimated_hours
        if trial_capped:
            capped_count += 1
        if trial_timed_out:
            timed_out_count += 1
        if i == 0:
            opening_death = simulated_battles <= 1 and simulated_fights <= 0.0
        i += 1

        need_more_trials = (
            (not opening_death)
            and (executed_trials >= trials)
            and (total_simulated_battles < MIN_TOTAL_SIMULATED_BATTLES)
            and (executed_trials < MAX_DYNAMIC_TRIALS)
        )
        if executed_trials < trials or need_more_trials:
            continue
        break

    avg_fights = total_estimated_fights / executed_trials if executed_trials > 0 else 0.0
    avg_total_hours = total_estimated_hours / executed_trials if executed_trials > 0 else 0.0

    infinite_fights = infinite_trial_count >= trials
    if infinite_fights:
        if total_simulated_fights_for_infinite > 0.0:
            # 30场无损时不加恢复时间，直接按模拟样本的单场时间估算效率。
            avg_single_fight_hours = total_simulated_hours_for_infinite / total_simulated_fights_for_infinite
        else:
            avg_single_fight_hours = 0.0
    else:
        avg_single_fight_hours = (
            (avg_total_hours + DEATH_RECOVER_SECONDS / 3600.0) / avg_fights
            if avg_fights > 0.0
            else 0.0
        )

    avg_fights_per_hour = (1.0 / avg_single_fight_hours) if avg_single_fight_hours > 0.0 else 0.0
    avg_item_per_hour: Dict[str, float] = {}
    if avg_fights_per_hour > 0.0:
        expected_per_fight = _calculate_expected_drops_per_fight(area_cfg)
        for item_id, expected_value in expected_per_fight.items():
            avg_item_per_hour[item_id] = expected_value * avg_fights_per_hour

    return {
        "avg_fights": avg_fights,
        "avg_total_hours": avg_total_hours,
        "avg_single_fight_hours": avg_single_fight_hours,
        "avg_fights_per_hour": avg_fights_per_hour,
        "avg_item_per_hour": avg_item_per_hour,
        "capped_rate": (capped_count / executed_trials) if executed_trials > 0 else 0.0,
        "timed_out_rate": (timed_out_count / executed_trials) if executed_trials > 0 else 0.0,
        "infinite_fights": infinite_fights,
        "executed_trials": executed_trials,
        "total_simulated_battles": total_simulated_battles,
    }


def build_player_attrs_from_realm(realms_data: Dict[str, Any], realm_name: str, level: int) -> Dict[str, float]:
    realm = realms_data["realms"].get(realm_name, {})
    level_data = realm.get("levels", {}).get(str(level), {})
    if not level_data:
        raise ValueError(f"invalid realm/level: {realm_name}-{level}")
    return {
        "health": float(level_data.get("health", 1.0)),
        "attack": float(level_data.get("attack", 1.0)),
        "defense": float(level_data.get("defense", 0.0)),
        "speed": float(realm.get("speed", 5.0)),
    }


def build_checkpoint_matrix(
    realms_data: Dict[str, Any],
    areas_data: Dict[str, Any],
    enemies_data: Dict[str, Any],
    *,
    k_value: float,
    skill_coef: float,
    checkpoints: tuple[int, ...] = (1, 4, 7),
    trials: int = DEFAULT_TRIALS,
    max_fights_per_trial: int = DEFAULT_MAX_FIGHTS_PER_TRIAL,
    battle_interval_seconds: float = DEFAULT_BATTLE_INTERVAL_SECONDS,
    penetration: float = 0.0,
    seed: Optional[int] = None,
    target_realms: Optional[tuple[str, ...]] = None,
) -> Dict[str, Any]:
    summary_rows = []
    reward_rows = []
    normal_areas = areas_data.get("normal_areas", {})

    allowed_realms = set(target_realms) if target_realms else None
    for realm_name in realms_data.get("realm_order", []):
        if allowed_realms and realm_name not in allowed_realms:
            continue
        max_level = int(realms_data.get("realms", {}).get(realm_name, {}).get("max_level", 0))
        for level in checkpoints:
            if level > max_level:
                continue
            player_attrs = build_player_attrs_from_realm(realms_data, realm_name, level)
            for area_id, area_cfg in normal_areas.items():
                area_name = str(area_cfg.get("name", area_id))
                seed_offset = sum(ord(ch) for ch in f"{realm_name}:{level}:{area_id}")
                area_seed = None if seed is None else int(seed) + seed_offset
                avg_result = simulate_average(
                    player_attrs=player_attrs,
                    area_cfg=area_cfg,
                    enemies_data=enemies_data,
                    k_value=k_value,
                    skill_coef=skill_coef,
                    penetration=penetration,
                    trials=trials,
                    max_fights_per_trial=max_fights_per_trial,
                    battle_interval_seconds=battle_interval_seconds,
                    seed=area_seed,
                )
                summary_rows.append(
                    {
                        "realm_name": realm_name,
                        "level": level,
                        "area_id": str(area_id),
                        "area_name": area_name,
                        "avg_fights": avg_result["avg_fights"],
                        "infinite_fights": avg_result.get("infinite_fights", False),
                        "avg_total_hours": avg_result["avg_total_hours"],
                        "avg_fights_per_hour": avg_result["avg_fights_per_hour"],
                        "capped_rate": avg_result["capped_rate"],
                        "timed_out_rate": avg_result["timed_out_rate"],
                    }
                )
                for item_id, value in avg_result["avg_item_per_hour"].items():
                    reward_rows.append(
                        {
                            "realm_name": realm_name,
                            "level": level,
                            "area_id": str(area_id),
                            "area_name": area_name,
                            "item_id": str(item_id),
                            "avg_per_hour": value,
                        }
                    )
    return {"summary_rows": summary_rows, "reward_rows": reward_rows}
