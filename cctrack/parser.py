import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import get_claude_projects_dir


@dataclass
class TokenEntry:
    session_id: str
    timestamp: datetime
    model: str
    project: str          # derived from the directory name
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    provider: str = "claude"


def _parse_project_name(jsonl_path: Path) -> str:
    # ~/.claude/projects/-home-user-projects-myapp/session.jsonl
    # convert the directory slug back to a readable path
    slug = jsonl_path.parent.name
    return slug.lstrip("-").replace("-", "/")


def parse_file(jsonl_path: Path) -> list[TokenEntry]:
    project = _parse_project_name(jsonl_path)
    entries: list[TokenEntry] = []

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("type") != "assistant":
                continue

            msg = record.get("message", {})
            usage = msg.get("usage")
            if not usage:
                continue

            ts_raw = record.get("timestamp")
            if not ts_raw:
                continue

            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                continue

            entries.append(TokenEntry(
                session_id=record.get("sessionId", ""),
                timestamp=ts,
                model=msg.get("model", "unknown"),
                project=project,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_write_tokens=usage.get("cache_creation_input_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            ))

    return entries


def parse_all() -> list[TokenEntry]:
    base = get_claude_projects_dir()
    if not base.exists():
        return []

    all_entries: list[TokenEntry] = []
    for jsonl_file in base.glob("**/*.jsonl"):
        all_entries.extend(parse_file(jsonl_file))

    all_entries.sort(key=lambda e: e.timestamp)
    return all_entries
