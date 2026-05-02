from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REALMS_PATH = DATA_DIR / "realms.json"
RECIPES_PATH = DATA_DIR / "recipes.json"
AREAS_PATH = DATA_DIR / "areas.json"
ENEMIES_PATH = DATA_DIR / "enemies.json"
ITEMS_PATH = DATA_DIR / "items.json"
SPELLS_PATH = DATA_DIR / "spells.json"

SERVER_ROOT = PROJECT_ROOT.parent / "idle_cultivation_server"
SERVER_REALMS_PATH = SERVER_ROOT / "app/game/content/cultivation/realms.json"
SERVER_RECIPES_PATH = SERVER_ROOT / "app/game/content/alchemy/recipes.json"
SERVER_AREAS_PATH = SERVER_ROOT / "app/game/content/lianli/areas.json"
SERVER_ENEMIES_PATH = SERVER_ROOT / "app/game/content/lianli/enemies.json"
SERVER_ITEMS_PATH = SERVER_ROOT / "app/game/content/inventory/items.json"
SERVER_SPELLS_PATH = SERVER_ROOT / "app/game/content/spell/spells.json"
