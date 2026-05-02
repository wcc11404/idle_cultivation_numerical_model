from src.io.data_paths import SPELLS_PATH
from src.io.data_sync import ensure_local_data


def test_ensure_local_data_includes_spells():
    assert SPELLS_PATH.exists(), f"spells data file should exist: {SPELLS_PATH}"
    ensure_local_data()
