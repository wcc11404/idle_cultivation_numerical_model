from src.model.realm_generator import apply_generation_rules


def _sample_realms():
    return {
        "realm_order": ["炼气期", "筑基期", "金丹期"],
        "realms": {
            "炼气期": {
                "max_level": 3,
                "levels": {
                    "1": {"spirit_energy_cost": 10, "max_spirit_energy": 10},
                    "2": {"spirit_energy_cost": 20, "max_spirit_energy": 20},
                    "3": {"spirit_energy_cost": 30, "max_spirit_energy": 30},
                },
            },
            "筑基期": {
                "max_level": 3,
                "levels": {
                    "1": {"spirit_energy_cost": 100, "max_spirit_energy": 80},
                    "2": {"spirit_energy_cost": 0, "max_spirit_energy": 0},
                    "3": {"spirit_energy_cost": 0, "max_spirit_energy": 0},
                },
            },
            "金丹期": {
                "max_level": 3,
                "levels": {
                    "1": {"spirit_energy_cost": 0, "max_spirit_energy": 0},
                    "2": {"spirit_energy_cost": 0, "max_spirit_energy": 0},
                    "3": {"spirit_energy_cost": 0, "max_spirit_energy": 0},
                },
            },
        },
    }


def test_apply_generation_rules_keeps_lianqi_manual_and_generates_following_realms():
    data = _sample_realms()
    result = apply_generation_rules(
        realms_data=data,
        lianqi_costs={1: 11, 2: 22, 3: 33},
        lianqi_max_spirits={1: 15, 2: 25, 3: 35},
        foundation_base_cost=200,
        foundation_base_max_spirit=150,
        level_multiplier=1.1,
        realm_multiplier=5.0,
    )

    assert result["realms"]["炼气期"]["levels"]["2"]["spirit_energy_cost"] == 22
    assert result["realms"]["炼气期"]["levels"]["3"]["max_spirit_energy"] == 35

    assert result["realms"]["筑基期"]["levels"]["1"]["spirit_energy_cost"] == 200
    assert result["realms"]["筑基期"]["levels"]["2"]["spirit_energy_cost"] == 220
    assert result["realms"]["筑基期"]["levels"]["3"]["spirit_energy_cost"] == 242

    assert result["realms"]["筑基期"]["levels"]["1"]["max_spirit_energy"] == 150
    assert result["realms"]["筑基期"]["levels"]["2"]["max_spirit_energy"] == 165

    assert result["realms"]["金丹期"]["levels"]["1"]["spirit_energy_cost"] == 1000
    assert result["realms"]["金丹期"]["levels"]["1"]["max_spirit_energy"] == 750
