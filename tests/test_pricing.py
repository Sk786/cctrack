import json

import pytest

from cctrack.config import get_bundled_prices_path, load_prices
from cctrack.stats import calc_cost


def _write_user_prices(tmp_path, monkeypatch, models: dict) -> None:
    path = tmp_path / "prices.json"
    path.write_text(json.dumps({"models": models, "default": {"input": 1, "output": 2, "cache_write": 0, "cache_read": 0}}))
    monkeypatch.setattr("cctrack.config._USER_PRICES", path)


def test_longest_prefix_wins(tmp_path, monkeypatch):
    """gpt-4o-mini must not resolve to the gpt-4o entry."""
    _write_user_prices(
        tmp_path,
        monkeypatch,
        {
            "gpt-4o": {"input": 2.5, "output": 10, "cache_write": 0, "cache_read": 1.25},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6, "cache_write": 0, "cache_read": 0.075},
        },
    )

    assert calc_cost("gpt-4o-mini", 1_000_000, 0, 0, 0) == pytest.approx(0.15)
    assert calc_cost("gpt-4o", 1_000_000, 0, 0, 0) == pytest.approx(2.5)


def test_bundled_prices_cover_codex_models():
    models = load_prices()["models"]

    for key in ("gpt-5.6-sol", "gpt-5.2-codex", "gpt-5.1-codex-mini", "gpt-4o-mini"):
        assert key in models, f"{key} missing from bundled prices"


def test_bundled_prices_are_complete():
    for name, prices in load_prices()["models"].items():
        for field in ("input", "output", "cache_write", "cache_read"):
            assert isinstance(prices[field], (int, float)), f"{name}.{field}"


def test_bundled_prices_file_exists():
    assert get_bundled_prices_path().is_file()
