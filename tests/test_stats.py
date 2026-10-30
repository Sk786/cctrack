from cctrack.stats import calc_cost, summarize_rows, daily_breakdown
from datetime import date, timedelta


def test_calc_cost_prefers_reported_cost():
    # OpenCode records the cost it was actually billed; that wins over the table.
    assert calc_cost("unknown-model", 1_000_000, 0, 0, 0, reported_cost=0.0) == 0.0
    assert calc_cost("claude-sonnet-4-6", 1_000_000, 0, 0, 0, reported_cost=0.42) == 0.42


def test_reasoning_is_not_billed_twice():
    # Providers report output_tokens as already including reasoning, so the
    # reasoning count must not change the cost.
    base = calc_cost("claude-sonnet-4-6", 0, 1_000_000, 0, 0)
    with_reasoning = calc_cost("claude-sonnet-4-6", 0, 1_000_000, 0, 0, reasoning_tokens=400_000)
    assert abs(base - 15.0) < 0.0001
    assert base == with_reasoning


def test_summarize_rows_uses_reported_cost_and_counts_reasoning():
    rows = [
        {
            "model": "deepseek-v4.1-flash-free",
            "input_tokens": 100,
            "output_tokens": 20,
            "cache_write_tokens": 0,
            "cache_read_tokens": 50,
            "reasoning_tokens": 5,
            "reported_cost": 0.0,
        }
    ]
    result = summarize_rows(rows)["deepseek-v4.1-flash-free"]
    assert result.cost == 0.0
    # reasoning is a subset of output, so it is not added again
    assert result.total_tokens == 170
    assert result.reasoning_tokens == 5


def test_calc_cost_zero():
    assert calc_cost("claude-sonnet-4-6", 0, 0, 0, 0) == 0.0


def test_calc_cost_known_model():
    # 1M input tokens at $3.00/M = $3.00
    cost = calc_cost("claude-sonnet-4-6", 1_000_000, 0, 0, 0)
    assert abs(cost - 3.00) < 0.0001


def test_calc_cost_fallback_model():
    # unknown model should use default pricing (same as sonnet)
    cost_unknown = calc_cost("claude-unknown-99", 1_000_000, 0, 0, 0)
    cost_default = calc_cost("claude-sonnet-4-6", 1_000_000, 0, 0, 0)
    assert abs(cost_unknown - cost_default) < 0.0001


def test_summarize_rows_empty():
    assert summarize_rows([]) == {}


def test_summarize_rows_aggregates():
    rows = [
        {
            "model": "claude-sonnet-4-6",
            "input_tokens": 100,
            "output_tokens": 200,
            "cache_write_tokens": 50,
            "cache_read_tokens": 10,
        },
        {
            "model": "claude-sonnet-4-6",
            "input_tokens": 100,
            "output_tokens": 200,
            "cache_write_tokens": 50,
            "cache_read_tokens": 10,
        },
    ]
    result = summarize_rows(rows)
    assert "claude-sonnet-4-6" in result
    s = result["claude-sonnet-4-6"]
    assert s.input_tokens == 200
    assert s.output_tokens == 400
    assert s.cost > 0


def test_summarize_rows_multiple_models():
    rows = [
        {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0},
        {"model": "claude-haiku-4-5", "input_tokens": 100, "output_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0},
    ]
    result = summarize_rows(rows)
    assert len(result) == 2
    assert "claude-sonnet-4-6" in result
    assert "claude-haiku-4-5" in result


def test_daily_breakdown_fills_empty_days():
    # pass empty rows — every day should have an empty DaySummary
    days = daily_breakdown([], days=7)
    assert len(days) == 7
    for day in days:
        assert day.total_cost == 0.0
        assert day.total_tokens == 0


def test_daily_breakdown_correct_dates():
    days = daily_breakdown([], days=7)
    today = date.today()
    assert days[-1].day == today
    assert days[0].day == today - timedelta(days=6)


def test_daily_breakdown_assigns_to_correct_day():
    today = date.today()
    rows = [
        {
            "timestamp": today.isoformat() + "T10:00:00",
            "model": "claude-sonnet-4-6",
            "input_tokens": 500,
            "output_tokens": 0,
            "cache_write_tokens": 0,
            "cache_read_tokens": 0,
        }
    ]
    days = daily_breakdown(rows, days=7)
    today_summary = next(d for d in days if d.day == today)
    assert today_summary.total_tokens == 500
