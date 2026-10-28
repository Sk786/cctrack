from datetime import date
from xml.etree import ElementTree

import pytest

from cctrack.heatmap import aggregate_daily, export_svg, render_heatmap


def _row(day: str, *, session: str = "s1", tokens: int = 10) -> dict:
    return {
        "timestamp": f"{day}T12:00:00",
        "session_id": session,
        "model": "claude-sonnet-4-6",
        "input_tokens": tokens,
        "output_tokens": 0,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
    }


def test_aggregate_daily_sums_tokens_and_counts_active_days_once():
    rows = [_row("2026-10-01"), _row("2026-10-01", session="s2", tokens=15)]

    assert aggregate_daily(rows, "tokens") == {date(2026, 10, 1): 25}
    assert aggregate_daily(rows, "active-days") == {date(2026, 10, 1): 1.0}


def test_aggregate_daily_calculates_estimated_cost():
    rows = [_row("2026-10-01", tokens=1_000_000)]

    assert aggregate_daily(rows, "cost")[date(2026, 10, 1)] == 3.0


def test_aggregate_daily_rejects_unknown_metric():
    with pytest.raises(ValueError, match="metric must be one of"):
        aggregate_daily([], "requests")


def test_render_heatmap_shows_period_total_and_legend():
    start = date(2026, 10, 1)
    output = render_heatmap({start: 250}, start, date(2026, 10, 7), "tokens")

    assert "250 tokens" in output.plain
    assert "Less" in output.plain and "More" in output.plain
    assert "Mo" in output.plain and "Su" in output.plain


def test_month_labels_do_not_collide():
    from cctrack.heatmap import _month_marks, _calendar

    start = date(2025, 10, 29)
    end = date(2026, 10, 28)
    _, weeks = _calendar(start, end)
    marks = _month_marks(weeks, start, end)

    assert [name for _, name in marks][:3] == ["Oct", "Dec", "Jan"]
    for (column, name), (next_column, _) in zip(marks, marks[1:]):
        assert next_column >= column + len(name) + 1


def test_export_svg_is_standalone_and_accessible(tmp_path):
    start = date(2026, 10, 1)
    path = export_svg(
        {start: 250}, start, date(2026, 10, 7), "tokens", tmp_path / "nested" / "heatmap.svg"
    )

    root = ElementTree.parse(path).getroot()
    content = path.read_text(encoding="utf-8")
    assert root.attrib["role"] == "img"
    assert root.attrib["aria-labelledby"] == "svg-title svg-desc"
    assert root.find(".//{http://www.w3.org/2000/svg}rect/{http://www.w3.org/2000/svg}title") is not None
    assert "Selected metric: tokens" in content
    assert "250" not in content
    assert ">Oct</text>" in content or ">Sep</text>" in content
