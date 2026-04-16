import shutil

from src.io.data_paths import (
    DATA_DIR,
    REALMS_PATH,
    RECIPES_PATH,
    AREAS_PATH,
    ENEMIES_PATH,
    ITEMS_PATH,
    SERVER_REALMS_PATH,
    SERVER_RECIPES_PATH,
    SERVER_AREAS_PATH,
    SERVER_ENEMIES_PATH,
    SERVER_ITEMS_PATH,
)


def ensure_local_data() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not REALMS_PATH.exists():
        raise FileNotFoundError(f"missing local data file: {REALMS_PATH}")
    if not RECIPES_PATH.exists():
        raise FileNotFoundError(f"missing local data file: {RECIPES_PATH}")
    if not AREAS_PATH.exists():
        raise FileNotFoundError(f"missing local data file: {AREAS_PATH}")
    if not ENEMIES_PATH.exists():
        raise FileNotFoundError(f"missing local data file: {ENEMIES_PATH}")
    if not ITEMS_PATH.exists():
        raise FileNotFoundError(f"missing local data file: {ITEMS_PATH}")


def sync_from_server() -> None:
    _copy(SERVER_REALMS_PATH, REALMS_PATH)
    _copy(SERVER_RECIPES_PATH, RECIPES_PATH)
    _copy(SERVER_AREAS_PATH, AREAS_PATH)
    _copy(SERVER_ENEMIES_PATH, ENEMIES_PATH)
    _copy(SERVER_ITEMS_PATH, ITEMS_PATH)

def _copy(src, dst) -> None:
    if not src.exists():
        raise FileNotFoundError(f"source file not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
