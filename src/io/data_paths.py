from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REALMS_PATH = DATA_DIR / "realms.json"
RECIPES_PATH = DATA_DIR / "recipes.json"

SERVER_ROOT = PROJECT_ROOT.parent / "idle_cultivation_server"
SERVER_REALMS_PATH = SERVER_ROOT / "app/modules/cultivation/realms.json"
SERVER_RECIPES_PATH = SERVER_ROOT / "app/modules/alchemy/recipes.json"
