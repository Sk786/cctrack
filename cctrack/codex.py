"""Read local token usage from the OpenAI Codex CLI.

Codex writes one rollout file per session:

    ~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl

Each line is a JSON event. ``turn_context`` events carry the active model and
working directory, and ``event_msg`` events of type ``token_count`` carry a
``last_token_usage`` delta for that turn. Rollout files are append-only, so
only files touched since the last sync need re-reading.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .parser import TokenEntry


def get_sessions_dir() -> Path | None:
    """Return the Codex sessions directory, or None when Codex isn't installed."""
    home = Path.home()
    candidates: list[Path] = []

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home) / "sessions")
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "codex" / "sessions")
    candidates.append(home / ".codex" / "sessions")

    for path in candidates:
        if path.is_dir():
            return path
    return None


def _timestamp(raw: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _rollout_files(base: Path, since: datetime | None) -> list[Path]:
    files = []
    for path in base.glob("**/rollout-*.jsonl"):
        if since is not None:
            try:
                if datetime.fromtimestamp(path.stat().st_mtime) < since:
                    continue
            except OSError:
                continue
        files.append(path)
    return files


def parse_sessions(days: int = 365, since: datetime | None = None) -> list[TokenEntry]:
    """Return usage entries from Codex rollout files.

    ``since`` limits work to files modified after that time; the first sync
    passes None and reads everything.
    """
    base = get_sessions_dir()
    if base is None:
        return []

    cutoff = datetime.now() - timedelta(days=days) if days else None
    entries: list[TokenEntry] = []

    for path in _rollout_files(base, since):
        session_id = path.stem
        model: str | None = None
        project = ""
        event_index = 0

        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"token_count"' not in line and '"turn_context"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue

                payload = event.get("payload") or {}
                kind = event.get("type")

                if kind == "turn_context":
                    model = payload.get("model") or model
                    cwd = payload.get("cwd")
                    if cwd:
                        project = str(cwd).replace("\\", "/").lstrip("/")
                    continue

                if kind != "event_msg" or payload.get("type") != "token_count":
                    continue

                usage = (payload.get("info") or {}).get("last_token_usage")
                if not usage:
                    continue

                totals = sum(
                    int(usage.get(key) or 0)
                    for key in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens")
                )
                if totals == 0:
                    continue

                timestamp = _timestamp(event.get("timestamp", ""))
                if timestamp is None or (cutoff and timestamp < cutoff):
                    continue

                cached = int(usage.get("cached_input_tokens") or 0)
                # Codex reports output_tokens as billable output, with reasoning
                # already included as a subset.
                entries.append(
                    TokenEntry(
                        # event index keeps duplicate same-millisecond turns distinct
                        session_id=f"{session_id}#{event_index}",
                        timestamp=timestamp,
                        model=model or "unknown",
                        project=project,
                        input_tokens=max(0, int(usage.get("input_tokens") or 0) - cached),
                        output_tokens=int(usage.get("output_tokens") or 0),
                        cache_write_tokens=0,
                        cache_read_tokens=cached,
                        provider="codex",
                        reasoning_tokens=int(usage.get("reasoning_output_tokens") or 0),
                        reported_cost=None,
                    )
                )
                event_index += 1

    return entries
