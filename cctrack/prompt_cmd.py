"""
Standalone entry point for `cctrack-prompt`.
Imports only stdlib — no typer, rich, or plotext — to stay under 50ms.
"""
import sys
import sqlite3
from pathlib import Path


def _db_path() -> Path:
    return Path.home() / ".config" / "cctrack" / "usage.db"


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def _load_prices() -> dict:
    import json
    user = Path.home() / ".config" / "cctrack" / "prices.json"
    bundled = Path(__file__).parent / "data" / "prices.json"
    path = user if user.exists() else bundled
    with open(path) as f:
        return json.load(f)


def _calc_cost(model: str, inp: int, out: int, cw: int, cr: int, prices: dict,
               reasoning: int = 0, reported_cost: float | None = None) -> float:
    if reported_cost is not None:
        return reported_cost
    models = prices.get("models", {})
    p = prices["default"]
    for key in models:
        if model.startswith(key):
            p = models[key]
            break
    per_m = 1_000_000
    return (
        inp * p["input"] / per_m
        + (out + reasoning) * p["output"] / per_m
        + cw * p["cache_write"] / per_m
        + cr * p["cache_read"] / per_m
    )


def main():
    fmt = "both"
    for i, arg in enumerate(sys.argv[1:]):
        if arg in ("--format", "-f") and i + 1 < len(sys.argv) - 1:
            fmt = sys.argv[i + 2]

    db = _db_path()
    if not db.exists():
        sys.exit(0)

    try:
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT model, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, "
            "reasoning_tokens, reported_cost "
            "FROM usage WHERE date(timestamp) = date('now', 'localtime')"
        ).fetchall()
        conn.close()
    except Exception:
        sys.exit(0)

    if not rows:
        sys.exit(0)

    try:
        prices = _load_prices()
    except Exception:
        prices = {"models": {}, "default": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30}}

    total_tokens = 0
    total_cost = 0.0
    for model, inp, out, cw, cr, reasoning, reported_cost in rows:
        total_tokens += inp + out + cw + cr + (reasoning or 0)
        total_cost += _calc_cost(
            model, inp, out, cw, cr, prices,
            reasoning=reasoning or 0, reported_cost=reported_cost,
        )

    if fmt == "tokens":
        out_str = f"[CC {_fmt(total_tokens)}]"
    elif fmt == "cost":
        out_str = f"[CC ${total_cost:.2f}]"
    else:
        out_str = f"[CC {_fmt(total_tokens)} · ${total_cost:.2f}]"

    print(out_str)


if __name__ == "__main__":
    main()
