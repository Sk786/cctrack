import json
from datetime import datetime, timedelta
from pathlib import Path

from cctrack.codex import get_sessions_dir, parse_sessions


def _rollout(path: Path, events: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
    return path


def _turn_context(model: str, cwd: str) -> dict:
    return {
        "timestamp": "2026-10-01T10:00:00.000Z",
        "type": "turn_context",
        "payload": {"model": model, "cwd": cwd},
    }


def _token_count(when: str, *, input_tokens: int, cached: int, output: int, reasoning: int = 0) -> dict:
    return {
        "timestamp": when,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached,
                    "output_tokens": output,
                    "reasoning_output_tokens": reasoning,
                }
            },
        },
    }


def test_parse_sessions_reads_token_events(tmp_path, monkeypatch):
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "10" / "01"
    _rollout(
        sessions / "rollout-2026-10-01T10-00-00-abc.jsonl",
        [
            _turn_context("gpt-5.6-sol", "/home/user/projects/app"),
            _token_count("2026-10-01T10:00:05.000Z", input_tokens=1000, cached=800, output=100, reasoning=40),
        ],
    )
    monkeypatch.setenv("CODEX_HOME", "")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    entries = parse_sessions()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.provider == "codex"
    assert entry.model == "gpt-5.6-sol"
    assert entry.project == "home/user/projects/app"
    # cached input is reported inside input_tokens
    assert entry.input_tokens == 200
    assert entry.cache_read_tokens == 800
    assert entry.output_tokens == 100
    assert entry.reasoning_tokens == 40
    assert entry.reported_cost is None


def test_parse_sessions_skips_null_and_old_events(tmp_path, monkeypatch):
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "10" / "01"
    old = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    _rollout(
        sessions / "rollout-a.jsonl",
        [
            _turn_context("gpt-5.1-codex", "/repo"),
            {"timestamp": "2026-10-01T10:00:00.000Z", "type": "event_msg",
             "payload": {"type": "token_count", "info": None}},
            _token_count(old, input_tokens=10, cached=0, output=1),
        ],
    )
    monkeypatch.setenv("CODEX_HOME", "")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    assert parse_sessions(days=30) == []


def test_duplicate_timestamps_stay_distinct(tmp_path, monkeypatch):
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "10" / "01"
    same = "2026-10-01T10:00:05.000Z"
    _rollout(
        sessions / "rollout-b.jsonl",
        [
            _turn_context("gpt-5.6-sol", "/repo"),
            _token_count(same, input_tokens=100, cached=0, output=10),
            _token_count(same, input_tokens=100, cached=0, output=10),
        ],
    )
    monkeypatch.setenv("CODEX_HOME", "")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    entries = parse_sessions()

    assert len(entries) == 2
    assert entries[0].session_id != entries[1].session_id


def test_returns_empty_without_codex(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", "")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))

    assert get_sessions_dir() is None
    assert parse_sessions() == []
