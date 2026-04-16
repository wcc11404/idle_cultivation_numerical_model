from pathlib import Path

from src.io.realms_text_updater import save_realms_numeric_fields_preserve_format


def test_save_realms_numeric_fields_preserve_format(tmp_path: Path):
    original_text = """{
\t"realm_order": [
\t\t"炼气期"
\t],
\t"realms": {
\t\t"炼气期": {
\t\t\t"max_level": 2,
\t\t\t"levels": {
\t\t\t\t"1": {"health": 50, "attack": 5, "defense": 2, "spirit_stone_cost": 4, "spirit_energy_cost": 5, "max_spirit_energy": 5},
\t\t\t\t"2": {"health": 60, "attack": 6, "defense": 3, "spirit_stone_cost": 8, "spirit_energy_cost": 10, "max_spirit_energy": 10}
\t\t\t}
\t\t}
\t}
}
"""
    path = tmp_path / "realms.json"
    path.write_text(original_text, encoding="utf-8")

    old_data = {
        "realm_order": ["炼气期"],
        "realms": {
            "炼气期": {
                "levels": {
                    "1": {"health": 50, "attack": 5, "defense": 2, "spirit_stone_cost": 4, "spirit_energy_cost": 5, "max_spirit_energy": 5},
                    "2": {"health": 60, "attack": 6, "defense": 3, "spirit_stone_cost": 8, "spirit_energy_cost": 10, "max_spirit_energy": 10},
                }
            }
        },
    }
    new_data = {
        "realms": {
            "炼气期": {
                "levels": {
                    "1": {"health": 55, "attack": 7, "defense": 4, "spirit_stone_cost": 6, "spirit_energy_cost": 7, "max_spirit_energy": 8},
                    "2": {"health": 66, "attack": 8, "defense": 5, "spirit_stone_cost": 9, "spirit_energy_cost": 11, "max_spirit_energy": 12},
                }
            }
        }
    }

    save_realms_numeric_fields_preserve_format(path, old_data, new_data)
    updated = path.read_text(encoding="utf-8")

    assert '"1": {"health": 55, "attack": 7, "defense": 4, "spirit_stone_cost": 6, "spirit_energy_cost": 7, "max_spirit_energy": 8}' in updated
    assert '"2": {"health": 66, "attack": 8, "defense": 5, "spirit_stone_cost": 9, "spirit_energy_cost": 11, "max_spirit_energy": 12}' in updated
    assert '\t\t"炼气期": {' in updated
