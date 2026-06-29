import json
import platform
from pathlib import Path

_BUNDLED_PRICES = Path(__file__).parent / "data" / "prices.json"
_USER_PRICES = Path.home() / ".config" / "cctrack" / "prices.json"


def load_prices() -> dict:
    path = _USER_PRICES if _USER_PRICES.exists() else _BUNDLED_PRICES
    with open(path) as f:
        data = json.load(f)
    data["_source"] = str(path)
    return data


def get_pricing(model: str) -> tuple[dict[str, float], str]:
    """Return (price_dict, source_path) for a model name."""
    data = load_prices()
    models: dict = data.get("models", {})
    for key, prices in models.items():
        if model.startswith(key):
            return prices, data["_source"]
    return data["default"], data["_source"]


def get_claude_projects_dir() -> Path:
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Roaming" / "Claude" / "projects"
    return Path.home() / ".claude" / "projects"


def get_user_prices_path() -> Path:
    return _USER_PRICES


def get_bundled_prices_path() -> Path:
    return _BUNDLED_PRICES
