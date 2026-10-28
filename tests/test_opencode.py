import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from cctrack.opencode import get_db_path, parse_db


def _make_db(path: Path, messages: list[dict], directory: str = "/home/user/projects/app") -> Path:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE message (
               id TEXT PRIMARY KEY,
               session_id TEXT NOT NULL,
               time_created INTEGER NOT NULL,
               data TEXT NOT NULL
           )"""
    )
    conn.execute("INSERT INTO session (id, directory) VALUES (?, ?)", ("ses_1", directory))
    for index, message in enumerate(messages):
        conn.execute(
            "INSERT INTO message (id, session_id, time_created, data) VALUES (?, ?, ?, ?)",
            (
                f"msg_{index}",
                message.get("session_id", "ses_1"),
                message["time_created"],
                json.dumps(message["data"]),
            ),
        )
    conn.commit()
    conn.close()
    return path


def _assistant(created: datetime, **tokens) -> dict:
    return {
        "time_created": int(created.timestamp() * 1000),
        "data": {
            "role": "assistant",
            "modelID": "deepseek-v4.1-flash-free",
            "providerID": "opencode",
            "cost": 0,
            "tokens": {
                "input": tokens.get("input", 100),
                "output": tokens.get("output", 20),
                "reasoning": tokens.get("reasoning", 5),
                "cache": {"write": tokens.get("cache_write", 0), "read": tokens.get("cache_read", 50)},
            },
        },
    }


def test_parse_db_reads_assistant_usage(tmp_path, monkeypatch):
    now = datetime.now().replace(microsecond=0)
    db = _make_db(tmp_path / "opencode.db", [_assistant(now)])
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path.parent))
    (tmp_path.parent / "opencode").mkdir(exist_ok=True)
    db.replace(tmp_path.parent / "opencode" / "opencode.db")

    entries = parse_db(days=7)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.provider == "opencode"
    assert entry.model == "deepseek-v4.1-flash-free"
    assert entry.input_tokens == 100
    assert entry.output_tokens == 20
    assert entry.reasoning_tokens == 5
    assert entry.cache_read_tokens == 50
    assert entry.reported_cost == 0.0
    assert entry.project == "home/user/projects/app"


def test_parse_db_skips_user_messages_and_old_rows(tmp_path, monkeypatch):
    now = datetime.now().replace(microsecond=0)
    old = now - timedelta(days=400)
    user_message = {
        "time_created": int(now.timestamp() * 1000),
        "data": {"role": "user", "tokens": {"input": 10}},
    }
    root = tmp_path / "share"
    (root / "opencode").mkdir(parents=True)
    _make_db(root / "opencode" / "opencode.db", [_assistant(now), _assistant(old), user_message])
    monkeypatch.setenv("XDG_DATA_HOME", str(root))

    entries = parse_db(days=30)

    assert len(entries) == 1


def test_parse_db_returns_empty_without_database(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "missing"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))

    assert get_db_path() is None
    assert parse_db() == []
