import random

from src.model.battle_model import (
    build_checkpoint_matrix,
    calculate_damage,
    DEATH_RECOVER_SECONDS,
    generate_enemy_for_area,
    simulate_average,
    simulate_trial,
)


def _mock_realms():
    return {
        "realm_order": ["炼气期", "筑基期"],
        "realms": {
            "炼气期": {
                "max_level": 5,
                "speed": 5.0,
                "levels": {
                    "1": {"health": 40, "attack": 8, "defense": 2},
                    "4": {"health": 60, "attack": 12, "defense": 4},
                    "5": {"health": 70, "attack": 14, "defense": 5},
                },
            },
            "筑基期": {
                "max_level": 8,
                "speed": 6.0,
                "levels": {
                    "1": {"health": 90, "attack": 20, "defense": 8},
                    "4": {"health": 120, "attack": 24, "defense": 10},
                    "5": {"health": 130, "attack": 25, "defense": 11},
                    "7": {"health": 150, "attack": 28, "defense": 12},
                },
            },
        },
    }


def _mock_areas():
    return {
        "normal_areas": {
            "demo_area": {
                "name": "演示区域",
                "enemies_template": [
                    {
                        "weight": 3,
                        "enemies": [{"template": "wolf", "min_level": 2, "max_level": 3}],
                        "drops": {"spirit_stone": {"min": 1, "max": 1, "chance": 1.0}},
                    },
                    {
                        "weight": 1,
                        "enemies": [{"template": "boar", "min_level": 4, "max_level": 5}],
                        "drops": {"spirit_stone": {"min": 2, "max": 2, "chance": 1.0}},
                    },
                ],
            }
        },
        "daily_areas": {},
        "tower": {},
    }


def _mock_enemies():
    return {
        "templates": {
            "wolf": {
                "growth": {
                    "health_base": 20,
                    "health_growth": 1.1,
                    "attack_base": 4,
                    "attack_growth": 1.1,
                    "defense_base": 1,
                    "defense_growth": 1.1,
                    "speed_base": 4.0,
                    "speed_growth": 0.0,
                }
            },
            "boar": {
                "growth": {
                    "health_base": 30,
                    "health_growth": 1.1,
                    "attack_base": 5,
                    "attack_growth": 1.1,
                    "defense_base": 2,
                    "defense_growth": 1.1,
                    "speed_base": 3.5,
                    "speed_growth": 0.0,
                }
            },
        }
    }


def _mock_enemies_never_act():
    data = _mock_enemies()
    for template in data["templates"].values():
        template["growth"]["speed_base"] = 0.0
        template["growth"]["speed_growth"] = 0.0
    return data


def test_damage_formula_boundary_and_monotonic():
    low_def = calculate_damage(attack=100, defense=0, penetration=0, k_value=500, skill_coef=1.0)
    high_def = calculate_damage(attack=100, defense=1000, penetration=0, k_value=500, skill_coef=1.0)
    higher_k = calculate_damage(attack=100, defense=1000, penetration=0, k_value=1000, skill_coef=1.0)

    assert low_def == 100.0
    assert high_def >= 1.0
    assert high_def < low_def
    assert higher_k > high_def

    scaled = calculate_damage(attack=100, defense=500, penetration=0, k_value=500, skill_coef=1.5)
    base = calculate_damage(attack=100, defense=500, penetration=0, k_value=500, skill_coef=1.0)
    assert abs(scaled - base * 1.5) < 1e-9


def test_enemy_generation_respects_templates_and_level_range():
    rng = random.Random(42)
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()

    for _ in range(200):
        generated = generate_enemy_for_area(area, enemies, rng)
        assert generated["template_id"] in {"wolf", "boar"}
        if generated["template_id"] == "wolf":
            assert 2 <= generated["level"] <= 3
        if generated["template_id"] == "boar":
            assert 4 <= generated["level"] <= 5


def test_simulate_trial_marks_capped_when_reaching_limit():
    player_attrs = {"health": 1000.0, "attack": 100.0, "defense": 50.0, "speed": 8.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()

    result = simulate_trial(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        penetration=0.0,
        max_fights_per_trial=3,
        seed=7,
    )

    assert result["victory_count"] == 3
    assert result["capped"] is True
    assert result["total_time_hours"] > 0.0


def test_battle_interval_seconds_increases_total_time():
    player_attrs = {"health": 1000.0, "attack": 100.0, "defense": 50.0, "speed": 8.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()

    base = simulate_trial(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        penetration=0.0,
        max_fights_per_trial=3,
        battle_interval_seconds=0.0,
        seed=7,
    )
    with_gap = simulate_trial(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        penetration=0.0,
        max_fights_per_trial=3,
        battle_interval_seconds=4.0,
        seed=7,
    )

    assert with_gap["victory_count"] == base["victory_count"] == 3
    # 3场战斗有2个场间间隔
    assert abs(with_gap["total_time_seconds"] - base["total_time_seconds"] - 8.0) < 1e-9


def test_simulate_trial_adds_recover_time_when_dead():
    player_attrs = {"health": 5.0, "attack": 1.0, "defense": 0.0, "speed": 1.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()
    result = simulate_trial(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        penetration=0.0,
        max_fights_per_trial=10,
        seed=1,
    )
    assert result["victory_count"] == 0
    # 恢复时间不在 trial 内加入，而是在 average 阶段统一计算。
    assert result["total_time_seconds"] < DEATH_RECOVER_SECONDS


def test_simulate_average_zero_wins_when_opening_fight_fails():
    player_attrs = {"health": 5.0, "attack": 1.0, "defense": 0.0, "speed": 1.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()
    result = simulate_average(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        trials=3,
        max_fights_per_trial=30,
        penetration=0.0,
        seed=2,
    )
    assert result["avg_fights"] == 0.0
    assert result["avg_fights_per_hour"] == 0.0
    assert result["avg_item_per_hour"] == {}
    # 上来就死场景不强制补采样。
    assert result["total_simulated_battles"] <= 10


def test_simulate_average_not_hard_clamped_to_30_fights_for_strong_player():
    player_attrs = {"health": 5000.0, "attack": 1000.0, "defense": 200.0, "speed": 12.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()
    result = simulate_average(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        trials=3,
        max_fights_per_trial=30,
        penetration=0.0,
        seed=3,
    )
    assert result["avg_fights"] >= 30.0


def test_simulate_average_ensures_minimum_sampled_battles_when_not_opening_death():
    player_attrs = {"health": 18.0, "attack": 12.0, "defense": 1.0, "speed": 5.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()
    result = simulate_average(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        trials=3,
        max_fights_per_trial=30,
        penetration=0.0,
        battle_interval_seconds=0.0,
        seed=21,
    )
    assert result["avg_fights"] > 0.0
    assert result["total_simulated_battles"] > 10
    assert result["executed_trials"] >= 3


def test_simulate_average_uses_analytic_drop_expectation():
    player_attrs = {"health": 1000.0, "attack": 200.0, "defense": 50.0, "speed": 10.0}
    area = {
        "name": "掉落校验区域",
        "enemies_template": [
            {
                "weight": 1,
                "enemies": [{"template": "wolf", "min_level": 1, "max_level": 1}],
                "drops": {
                    "spirit_stone": {"min": 1, "max": 3, "chance": 0.5},
                    "mat_herb": {"min": 2, "max": 2, "chance": 1.0},
                },
            },
            {
                "weight": 3,
                "enemies": [{"template": "boar", "min_level": 1, "max_level": 1}],
                "drops": {
                    "spirit_stone": {"min": 4, "max": 4, "chance": 1.0},
                },
            },
        ],
    }
    enemies = _mock_enemies()
    result = simulate_average(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        trials=3,
        max_fights_per_trial=30,
        penetration=0.0,
        battle_interval_seconds=0.0,
        seed=42,
    )
    assert result["avg_fights_per_hour"] > 0.0
    # spirit_stone: (1/4)*(0.5*((1+3)/2)) + (3/4)*(1.0*4) = 3.25
    # mat_herb: (1/4)*(1.0*2) = 0.5
    spirit_per_fight = result["avg_item_per_hour"]["spirit_stone"] / result["avg_fights_per_hour"]
    herb_per_fight = result["avg_item_per_hour"]["mat_herb"] / result["avg_fights_per_hour"]
    assert abs(spirit_per_fight - 3.25) < 1e-9
    assert abs(herb_per_fight - 0.5) < 1e-9


def test_simulate_average_uses_plus_100_seconds_for_single_fight_time():
    player_attrs = {"health": 1000.0, "attack": 200.0, "defense": 20.0, "speed": 8.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies()
    result = simulate_average(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        trials=3,
        max_fights_per_trial=30,
        penetration=0.0,
        seed=13,
    )
    if result["avg_fights"] > 0.0 and not result.get("infinite_fights", False):
        expected = (result["avg_total_hours"] + DEATH_RECOVER_SECONDS / 3600.0) / result["avg_fights"]
        assert abs(result["avg_single_fight_hours"] - expected) < 1e-9


def test_simulate_average_marks_infinite_when_no_health_loss_after_cap():
    player_attrs = {"health": 5000.0, "attack": 1000.0, "defense": 200.0, "speed": 12.0}
    area = _mock_areas()["normal_areas"]["demo_area"]
    enemies = _mock_enemies_never_act()
    result = simulate_average(
        player_attrs=player_attrs,
        area_cfg=area,
        enemies_data=enemies,
        k_value=500.0,
        skill_coef=1.0,
        trials=3,
        max_fights_per_trial=30,
        penetration=0.0,
        seed=9,
    )
    assert result["infinite_fights"] is True
    assert result["avg_single_fight_hours"] > 0.0
    # 无限战斗口径下，不叠加+100秒恢复时间。
    expected = result["avg_total_hours"] / 30.0
    assert abs(result["avg_single_fight_hours"] - expected) < 1e-9


def test_checkpoint_matrix_covers_each_realm_147_and_normal_areas():
    matrix = build_checkpoint_matrix(
        realms_data=_mock_realms(),
        areas_data=_mock_areas(),
        enemies_data=_mock_enemies(),
        k_value=500.0,
        skill_coef=1.0,
        checkpoints=(1, 4, 7),
        trials=3,
        max_fights_per_trial=10,
        penetration=0.0,
        seed=11,
    )

    summary_rows = matrix["summary_rows"]
    reward_rows = matrix["reward_rows"]

    # 炼气期(max=5)覆盖1/4；筑基期(max=8)覆盖1/4/7；共5行，每行1个普通区域
    assert len(summary_rows) == 5
    assert {row["level"] for row in summary_rows if row["realm_name"] == "炼气期"} == {1, 4}
    assert {row["level"] for row in summary_rows if row["realm_name"] == "筑基期"} == {1, 4, 7}
    assert all(row["area_id"] == "demo_area" for row in summary_rows)

    assert len(reward_rows) > 0


def test_checkpoint_matrix_respects_target_realms_and_15_levels():
    matrix = build_checkpoint_matrix(
        realms_data=_mock_realms(),
        areas_data=_mock_areas(),
        enemies_data=_mock_enemies(),
        k_value=500.0,
        skill_coef=1.0,
        checkpoints=(1, 5),
        trials=2,
        max_fights_per_trial=10,
        penetration=0.0,
        seed=12,
        target_realms=("炼气期", "筑基期", "金丹期"),
    )
    summary_rows = matrix["summary_rows"]
    # 炼气期有1/5，筑基期有1/5，金丹期在mock中不存在
    assert {row["realm_name"] for row in summary_rows} == {"炼气期", "筑基期"}
    assert {row["level"] for row in summary_rows if row["realm_name"] == "炼气期"} == {1, 5}
    assert {row["level"] for row in summary_rows if row["realm_name"] == "筑基期"} == {1, 5}
