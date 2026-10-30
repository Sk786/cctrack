"""Read local token usage from OpenCode's SQLite store.

OpenCode keeps per-message usage in ``~/.local/share/opencode/opencode.db``.
Assistant messages carry a ``tokens`` object (input, output, reasoning,
cache read/write) plus a ``cost`` value the provider already calculated.

The database is opened read-only; cctrack never writes to it.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .parser import TokenEntry


def get_db_path() -> Path | None:
    """Return the first existing OpenCode database path, or None."""
    candidates: list[Path] = []

    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        candidates.append(Path(data_home) / "opencode" / "opencode.db")

    if sys.platform == "win32":
        for var in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if base:
                candidates.append(Path(base) / "opencode" / "opencode.db")

    candidates.append(Path.home() / ".local" / "share" / "opencode" / "opencode.db")
    candidates.append(Path.home() / "Library" / "Application Support" / "opencode" / "opencode.db")

    for path in candidates:
        if path.is_file():
            return path
    return None


def parse_db(days: int | None = 365) -> list[TokenEntry]:
    """Return usage entries from the local OpenCode database.

    Returns an empty list when OpenCode is not installed, the schema is
    unfamiliar, or the database is temporarily locked.
    """
    path = get_db_path()
    if path is None:
        return []

    cutoff = datetime.now() - timedelta(days=days) if days else None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return []

    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT m.session_id AS session_id,
                   m.time_created AS created,
                   m.data AS data,
                   s.directory AS directory
            FROM message AS m
            LEFT JOIN session AS s ON s.id = m.session_id
            """
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    entries: list[TokenEntry] = []
    for row in rows:
        try:
            data = json.loads(row["data"])
        except (TypeError, ValueError):
            continue
        if data.get("role") != "assistant":
            continue

        created = row["created"]
        if not created:
            continue
        timestamp = datetime.fromtimestamp(created / 1000)
        if cutoff and timestamp < cutoff:
            continue

        tokens = data.get("tokens") or {}
        cache = tokens.get("cache") or {}
        cost = data.get("cost")

        input_tokens = int(tokens.get("input") or 0)
        output_tokens = int(tokens.get("output") or 0)
        cache_write = int(cache.get("write") or 0)
        cache_read = int(cache.get("read") or 0)
        reasoning = int(tokens.get("reasoning") or 0)

        # Aborted or errored turns can be recorded without any usage.
        if input_tokens + output_tokens + cache_write + cache_read + reasoning == 0:
            continue

        entries.append(
            TokenEntry(
                session_id=row["session_id"],
                timestamp=timestamp,
                model=data.get("modelID") or "unknown",
                project=(row["directory"] or "").replace("\\", "/").lstrip("/"),
                input_tokens=input_tokens,
                # OpenCode reports reasoning as its own field, unlike Codex where
                # it is already part of output_tokens.
                output_tokens=output_tokens + reasoning,
                cache_write_tokens=cache_write,
                cache_read_tokens=cache_read,
                provider=data.get("providerID") or "opencode",
                reasoning_tokens=reasoning,
                reported_cost=float(cost) if isinstance(cost, (int, float)) else None,
            )
        )

    return entries
