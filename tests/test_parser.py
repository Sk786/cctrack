import json
import tempfile
from pathlib import Path
from datetime import timezone

from cctrack.parser import parse_file, _parse_project_name


def _make_jsonl(records: list[dict]) -> Path:
    tmp = tempfile.mkdtemp()
    p = Path(tmp) / "-home-user-projects-myapp" / "session.jsonl"
    p.parent.mkdir(parents=True)
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


def _assistant_record(model="claude-sonnet-4-6", input=100, output=200, cw=50, cr=10):
    return {
        "type": "assistant",
        "sessionId": "sess-abc123",
        "timestamp": "2026-06-29T10:00:00Z",
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input,
                "output_tokens": output,
                "cache_creation_input_tokens": cw,
                "cache_read_input_tokens": cr,
            },
        },
    }


def test_parse_file_returns_entries():
    path = _make_jsonl([_assistant_record()])
    entries = parse_file(path)
    assert len(entries) == 1
    e = entries[0]
    assert e.model == "claude-sonnet-4-6"
    assert e.input_tokens == 100
    assert e.output_tokens == 200
    assert e.cache_write_tokens == 50
    assert e.cache_read_tokens == 10
    assert e.session_id == "sess-abc123"


def test_parse_file_skips_non_assistant():
    records = [
        {"type": "human", "sessionId": "s1", "timestamp": "2026-06-29T10:00:00Z", "message": {}},
        _assistant_record(),
    ]
    entries = parse_file(_make_jsonl(records))
    assert len(entries) == 1


def test_parse_file_skips_missing_usage():
    record = {
        "type": "assistant",
        "sessionId": "s1",
        "timestamp": "2026-06-29T10:00:00Z",
        "message": {"model": "claude-sonnet-4-6"},
    }
    entries = parse_file(_make_jsonl([record]))
    assert len(entries) == 0


def test_parse_file_skips_invalid_json():
    tmp = tempfile.mkdtemp()
    p = Path(tmp) / "-home-user-projects-myapp" / "session.jsonl"
    p.parent.mkdir(parents=True)
    with open(p, "w") as f:
        f.write("not valid json\n")
        f.write(json.dumps(_assistant_record()) + "\n")
    entries = parse_file(p)
    assert len(entries) == 1


def test_parse_file_timestamp_parsed():
    path = _make_jsonl([_assistant_record()])
    entries = parse_file(path)
    assert entries[0].timestamp.tzinfo == timezone.utc


def test_parse_project_name():
    p = Path("/home/user/.claude/projects/-home-user-projects-myapp/session.jsonl")
    name = _parse_project_name(p)
    assert name == "home/user/projects/myapp"
