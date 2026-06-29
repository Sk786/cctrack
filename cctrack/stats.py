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
    cost: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_write_tokens + self.cache_read_tokens


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
) -> float:
    prices, _ = get_pricing(model)
    per_m = 1_000_000
    return (
        input_tokens * prices["input"] / per_m
        + output_tokens * prices["output"] / per_m
        + cache_write_tokens * prices["cache_write"] / per_m
        + cache_read_tokens * prices["cache_read"] / per_m
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
        s.cost += calc_cost(
            model,
            row["input_tokens"],
            row["output_tokens"],
            row["cache_write_tokens"],
            row["cache_read_tokens"],
        )
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
