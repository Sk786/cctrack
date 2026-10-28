from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from .config import get_pricing


@dataclass
class ModelStats:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    reasoning_tokens: int = 0
    cost: float = 0.0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
            + self.reasoning_tokens
        )


@dataclass
class DaySummary:
    day: date
    models: dict[str, ModelStats] = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        return sum(m.cost for m in self.models.values())

    @property
    def total_tokens(self) -> int:
        return sum(m.total_tokens for m in self.models.values())


def calc_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int,
    cache_read_tokens: int,
    reasoning_tokens: int = 0,
    reported_cost: float | None = None,
) -> float:
    """Return the cost for one usage row.

    A provider-reported cost (OpenCode records one per message) is
    authoritative. Otherwise the bundled price table is used, with
    reasoning tokens billed at the output rate.
    """
    if reported_cost is not None:
        return reported_cost

    prices, _ = get_pricing(model)
    per_m = 1_000_000
    return (
        input_tokens * prices["input"] / per_m
        + (output_tokens + reasoning_tokens) * prices["output"] / per_m
        + cache_write_tokens * prices["cache_write"] / per_m
        + cache_read_tokens * prices["cache_read"] / per_m
    )


def cost_for_row(row: dict) -> float:
    """Cost for a stored usage row, preferring a provider-reported value."""
    return calc_cost(
        row["model"],
        row.get("input_tokens", 0),
        row.get("output_tokens", 0),
        row.get("cache_write_tokens", 0),
        row.get("cache_read_tokens", 0),
        row.get("reasoning_tokens", 0),
        row.get("reported_cost"),
    )


def summarize_rows(rows: list[dict]) -> dict[str, ModelStats]:
    """Aggregate a flat list of DB rows into per-model stats."""
    stats: dict[str, ModelStats] = {}
    for row in rows:
        model = row["model"]
        if model not in stats:
            stats[model] = ModelStats(model=model)
        s = stats[model]
        s.input_tokens += row["input_tokens"]
        s.output_tokens += row["output_tokens"]
        s.cache_write_tokens += row["cache_write_tokens"]
        s.cache_read_tokens += row["cache_read_tokens"]
        s.reasoning_tokens += row.get("reasoning_tokens", 0)
        s.cost += cost_for_row(row)
    return stats


def daily_breakdown(rows: list[dict], days: int = 7) -> list[DaySummary]:
    """Group rows by date into DaySummary objects, filling empty days with zeroes."""
    by_day: dict[date, list[dict]] = defaultdict(list)
    for row in rows:
        d = date.fromisoformat(row["timestamp"][:10])
        by_day[d].append(row)

    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        result.append(DaySummary(day=d, models=summarize_rows(by_day.get(d, []))))
    return result
