"""Daily usage aggregation and GitHub-style activity heatmaps."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape
from pathlib import Path

from rich.text import Text

from .stats import cost_for_row

METRICS = ("tokens", "cost", "active-days")
# 0 is "no activity" — dark enough to recede like GitHub's empty cell.
_LEVEL_COLORS = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")
# Truecolor/256 ramps. Dark greys can quantize to the terminal background on
# 16-colour terminals, so those get a named ANSI ramp instead.
_LEVEL_STYLES = ("#3a3a3a", "#2d7a4a", "#2ea043", "#3fb950", "#7ee787")
_LEVEL_STYLES_ANSI = ("grey30", "green", "green", "bright_green", "bright_green")


def _level_styles(color_system: str | None) -> tuple[tuple[str, ...], bool]:
    """Return (ramp, low_color) for this terminal's colour depth.

    On 16-colour terminals dark greys quantize to the background, so the ramp
    falls back to named ANSI colours and empty days switch to a dot glyph.
    """
    if color_system in (None, "standard"):
        return _LEVEL_STYLES_ANSI, True
    return _LEVEL_STYLES, False


def aggregate_daily(rows: list[dict], metric: str = "tokens") -> dict[date, float]:
    """Aggregate stored usage rows into a date -> metric value mapping."""
    if metric not in METRICS:
        raise ValueError(f"metric must be one of: {', '.join(METRICS)}")

    values: dict[date, float] = {}
    for row in rows:
        day = date.fromisoformat(row["timestamp"][:10])
        tokens = sum(
            row.get(key, 0)
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_write_tokens",
                "cache_read_tokens",
            )
        )
        if metric == "tokens":
            amount = tokens
        elif metric == "cost":
            amount = cost_for_row(row)
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


def _month_marks(weeks: list[list[date]], start: date, end: date) -> list[tuple[int, str]]:
    """Return (column, label) pairs, skipping labels that would collide."""
    marks: list[tuple[int, str]] = []
    last_end = -2
    covered: tuple[int, int] | None = None
    for column, week in enumerate(weeks):
        visible_day = next((day for day in week if start <= day <= end), None)
        if not visible_day:
            continue
        key = (visible_day.year, visible_day.month)
        if key == covered:
            continue
        covered = key
        name = visible_day.strftime("%b")
        if column < last_end + 2:
            continue  # not enough room next to the previous label
        marks.append((column, name))
        last_end = column + len(name) - 1
    return marks


def _month_labels(weeks: list[list[date]], start: date, end: date) -> list[str]:
    """Place 3-letter month labels without letting them collide."""
    labels = [" "] * len(weeks)
    for column, name in _month_marks(weeks, start, end):
        for offset, char in enumerate(name):
            if column + offset < len(labels):
                labels[column + offset] = char
    return labels


def _month_header(
    weeks: list[list[date]], start: date, end: date, spaced: bool
) -> str:
    """Month labels laid out on the same grid as the day cells."""
    cell = 2 if spaced else 1
    total = len(weeks) * cell - (1 if spaced else 0)
    canvas = [" "] * max(total, 0)
    for column, name in _month_marks(weeks, start, end):
        x = column * cell
        for offset, char in enumerate(name):
            if 0 <= x + offset < len(canvas):
                canvas[x + offset] = char
    return "".join(canvas).rstrip()


def _metric_total(values: dict[date, float], metric: str) -> str:
    if metric == "tokens":
        return f"{sum(values.values()):,.0f} tokens"
    if metric == "cost":
        return f"${sum(values.values()):,.2f} estimated spend"
    return f"{sum(value > 0 for value in values.values())} active days"


# Terminal cells are about twice as tall as wide. An upper-half block fills the
# width and half the height, so cells read as squares with an even gap instead
# of the tall, sparse gaps a full square glyph produces.
_CELL_GLYPH = "▀"
_CELL_GLYPH_COMPACT = "▪"
_MONTH_PREFIX = 3


def render_heatmap(
    values: dict[date, float],
    start: date,
    end: date,
    metric: str = "tokens",
    width: int | None = None,
    color_system: str | None = "truecolor",
) -> Text:
    """Render a GitHub-style activity grid.

    Cells are spaced out when the terminal is wide enough so each day reads as
    its own square. At low colour depths the ramp falls back to named ANSI
    colours and empty days use a dot, so no cell can match the background.
    """
    _, weeks = _calendar(start, end)
    level_by_day = _levels(values)
    styles, low_color = _level_styles(color_system)
    spaced = width is None or _MONTH_PREFIX + len(weeks) * 2 <= width
    separator = " " if spaced else ""
    glyph = _CELL_GLYPH if spaced else _CELL_GLYPH_COMPACT
    empty_glyph = "·" if low_color else glyph

    output = Text()
    output.append(f"AI activity · {start:%b %d, %Y} – {end:%b %d, %Y}\n", style="bold")
    active_days = sum(value > 0 for value in values.values())
    output.append(f"{_metric_total(values, metric)} · {active_days} active days\n\n", style="dim")

    header = _month_header(weeks, start, end, spaced)
    output.append(" " * _MONTH_PREFIX)
    output.append(header)
    output.append("\n")

    for weekday, label in enumerate(("Mo", "", "We", "", "Fr", "", "Su")):
        output.append(f"{label:<{_MONTH_PREFIX}}", style="dim")
        cells = []
        for week in weeks:
            day = week[weekday]
            if day < start or day > end:
                cells.append((empty_glyph, styles[0]))
                continue
            level = level_by_day.get(day, 0)
            cells.append((empty_glyph if level == 0 else glyph, styles[level]))
        for index, (cell_glyph, cell_style) in enumerate(cells):
            output.append(cell_glyph, style=cell_style)
            if spaced and index < len(cells) - 1:
                output.append(" ")
        output.append("\n")

    output.append("\nLess ", style="dim")
    for level in range(5):
        output.append(empty_glyph if level == 0 else glyph, style=styles[level])
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
    months: list[str] = [
        f'<text x="{left + column * step}" y="{top - 12}" class="month">{name}</text>'
        for column, name in _month_marks(weeks, start, end)
    ]

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
