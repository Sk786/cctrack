"""Daily usage aggregation and GitHub-style activity heatmaps."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape
from pathlib import Path

from rich.text import Text

from .config import get_pricing

METRICS = ("tokens", "cost", "active-days")
_LEVEL_COLORS = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")
_LEVEL_STYLES = ("#484f58", "#3fb950", "#3fb950", "#56d364", "#7ee787")


def aggregate_daily(rows: list[dict], metric: str = "tokens") -> dict[date, float]:
    """Aggregate stored usage rows into a date -> metric value mapping."""
    if metric not in METRICS:
        raise ValueError(f"metric must be one of: {', '.join(METRICS)}")

    values: dict[date, float] = {}
    prices_by_model: dict[str, dict[str, float]] = {}
    for row in rows:
        day = date.fromisoformat(row["timestamp"][:10])
        tokens = sum(
            row.get(key, 0)
            for key in ("input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens")
        )
        if metric == "tokens":
            amount = tokens
        elif metric == "cost":
            model = row["model"]
            if model not in prices_by_model:
                prices_by_model[model], _ = get_pricing(model)
            prices = prices_by_model[model]
            amount = (
                row.get("input_tokens", 0) * prices["input"]
                + row.get("output_tokens", 0) * prices["output"]
                + row.get("cache_write_tokens", 0) * prices["cache_write"]
                + row.get("cache_read_tokens", 0) * prices["cache_read"]
            ) / 1_000_000
        else:
            amount = 1 if tokens > 0 else 0
        if metric == "active-days":
            values[day] = float(bool(values.get(day, 0) or amount))
        else:
            values[day] = values.get(day, 0) + amount

    return values


def _levels(values: dict[date, float]) -> dict[date, int]:
    """Map values to zero plus four relative-intensity levels."""
    active = sorted(value for value in values.values() if value > 0)
    if not active:
        return {day: 0 for day in values}

    result = {}
    for day, value in values.items():
        if value <= 0:
            result[day] = 0
        else:
            rank = sum(item <= value for item in active) / len(active)
            result[day] = min(4, max(1, int(rank * 4)))
    return result


def _calendar(start: date, end: date) -> tuple[date, list[list[date]]]:
    first_monday = start - timedelta(days=start.weekday())
    weeks: list[list[date]] = []
    current = first_monday
    while current <= end:
        weeks.append([current + timedelta(days=offset) for offset in range(7)])
        current += timedelta(days=7)
    return first_monday, weeks


def _metric_total(values: dict[date, float], metric: str) -> str:
    if metric == "tokens":
        return f"{sum(values.values()):,.0f} tokens"
    if metric == "cost":
        return f"${sum(values.values()):,.2f} estimated spend"
    return f"{sum(value > 0 for value in values.values())} active days"


def render_heatmap(
    values: dict[date, float], start: date, end: date, metric: str = "tokens"
) -> Text:
    """Render a compact, accessible-in-terminal activity grid."""
    _, weeks = _calendar(start, end)
    level_by_day = _levels(values)
    output = Text()
    output.append(f"AI activity · {start:%b %d, %Y} – {end:%b %d, %Y}\n", style="bold")
    output.append(f"{_metric_total(values, metric)} · relative intensity\n\n", style="dim")

    month_labels = [" "] * len(weeks)
    previous_month: tuple[int, int] | None = None
    for column, week in enumerate(weeks):
        visible_day = next((day for day in week if start <= day <= end), None)
        if visible_day and (visible_day.year, visible_day.month) != previous_month:
            for offset, char in enumerate(visible_day.strftime("%b")):
                if column + offset < len(month_labels):
                    month_labels[column + offset] = char
            previous_month = (visible_day.year, visible_day.month)

    output.append("    ")
    output.append("".join(month_labels))
    output.append("\n")

    for weekday, label in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
        output.append(f"{label}  ", style="dim")
        for week in weeks:
            day = week[weekday]
            if day < start or day > end:
                output.append(" ")
                continue
            level = level_by_day.get(day, 0)
            output.append("■", style=_LEVEL_STYLES[level])
        output.append("\n")

    output.append("\nLess ", style="dim")
    for level in range(5):
        output.append("■", style=_LEVEL_STYLES[level])
        output.append(" ")
    output.append("More  ·  ", style="dim")
    output.append(metric, style="bold")
    return output


def export_svg(
    values: dict[date, float], start: date, end: date, metric: str, path: Path
) -> Path:
    """Write a self-contained SVG heatmap and return its path."""
    _, weeks = _calendar(start, end)
    level_by_day = _levels(values)
    cell = 12
    gap = 3
    step = cell + gap
    left = 42
    top = 42
    width = left + len(weeks) * step + 8
    height = top + 7 * step + 54
    months: list[str] = []
    prev_month = None
    for column, week in enumerate(weeks):
        month_day = next((day for day in week if start <= day <= end), None)
        if month_day and (month_day.year, month_day.month) != prev_month:
            months.append(
                f'<text x="{left + column * step}" y="{top - 12}" class="month">{month_day:%b}</text>'
            )
            prev_month = (month_day.year, month_day.month)

    cells: list[str] = []
    for column, week in enumerate(weeks):
        for weekday, day in enumerate(week):
            if day < start or day > end:
                continue
            level = level_by_day.get(day, 0)
            x = left + column * step
            y = top + weekday * step
            tooltip = "no activity" if level == 0 else f"intensity {level} of 4"
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
                f'fill="{_LEVEL_COLORS[level]}"><title>{day.isoformat()}: {tooltip}</title></rect>'
            )

    weekdays = "".join(
        f'<text x="0" y="{top + i * step + 10}" class="weekday">{name}</text>'
        for i, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))
    )
    title = f"AI activity · {start:%b %d, %Y} – {end:%b %d, %Y}"
    description = f"Selected metric: {metric}. Color shows relative daily activity intensity."
    legend_y = top + 7 * step + 15
    legend = (
        f'<text x="{left}" y="{legend_y + 9}" class="legend-label">Less</text>'
        + "".join(
            f'<rect x="{left + 34 + level * 16}" y="{legend_y}" width="11" height="11" '
            f'rx="3" fill="{_LEVEL_COLORS[level]}"/>'
            for level in range(5)
        )
        + f'<text x="{left + 122}" y="{legend_y + 9}" class="legend-label">More</text>'
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="svg-title svg-desc"
  viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <title id="svg-title">{escape(title)}</title>
  <desc id="svg-desc">{escape(description)}</desc>
  <style>text {{ font-family: system-ui, sans-serif; fill: #c9d1d9; }}
    .title {{ font-size: 14px; font-weight: 650; }} .subtitle {{ font-size: 11px; fill: #8b949e; }}
    .month {{ font-size: 10px; fill: #8b949e; }} .weekday {{ font-size: 9px; fill: #8b949e; }}
    .legend-label {{ font-size: 9px; fill: #8b949e; }}</style>
  <rect width="100%" height="100%" rx="12" fill="#0d1117"/>
  <text x="0" y="16" class="title">{escape(title)}</text>
  <text x="0" y="32" class="subtitle">{escape(description)}</text>
  {''.join(months)}{weekdays}{''.join(cells)}{legend}
</svg>'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return path
