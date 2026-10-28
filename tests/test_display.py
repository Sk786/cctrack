from cctrack.display import short_model, summarize_models


def test_short_model_drops_snapshot_date():
    assert short_model("claude-haiku-4-5-20251001") == "claude-haiku-4-5"
    assert short_model("claude-sonnet-4-6") == "claude-sonnet-4-6"
    assert short_model("gpt-6-luna") == "gpt-6-luna"
    assert short_model("deepseek-v4.1-flash-free") == "deepseek-v4.1-flash-free"


def test_summarize_models_is_sorted_deduplicated_and_capped():
    models = {"claude-sonnet-4-6", "claude-sonnet-4-6-20250101", "gpt-6-luna", "beam-free"}

    assert summarize_models(models) == "beam-free, claude-sonnet-4-6, gpt-6-luna"
    assert summarize_models(models, limit=2) == "beam-free, claude-sonnet-4-6 +1"
