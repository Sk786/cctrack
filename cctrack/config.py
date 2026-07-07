import json
import os
import platform
from pathlib import Path

_BUNDLED_PRICES = Path(__file__).parent / "data" / "prices.json"
_USER_PRICES = Path.home() / ".config" / "cctrack" / "prices.json"
_OPENAI_KEY_FILE = Path.home() / ".config" / "cctrack" / "openai_key"


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


def get_openai_api_key() -> str | None:
    """Return the OpenAI API key from env var or stored key file, else None."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    if _OPENAI_KEY_FILE.exists():
        key = _OPENAI_KEY_FILE.read_text().strip()
        if key:
            return key
    return None


def save_openai_api_key(key: str) -> None:
    _OPENAI_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _OPENAI_KEY_FILE.write_text(key.strip())
    _OPENAI_KEY_FILE.chmod(0o600)


def get_openai_key_path() -> Path:
    return _OPENAI_KEY_FILE
