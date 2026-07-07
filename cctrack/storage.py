import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from .parser import TokenEntry, parse_all


def get_db_path() -> Path:
    path = Path.home() / ".config" / "cctrack" / "usage.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _connect():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                project TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cache_write_tokens INTEGER NOT NULL DEFAULT 0,
                cache_read_tokens INTEGER NOT NULL DEFAULT 0,
                provider TEXT NOT NULL DEFAULT 'claude',
                PRIMARY KEY (session_id, timestamp)
            )
        """)
        # migrate existing DBs that lack the provider column
        cols = {row[1] for row in conn.execute("PRAGMA table_info(usage)").fetchall()}
        if "provider" not in cols:
            conn.execute("ALTER TABLE usage ADD COLUMN provider TEXT NOT NULL DEFAULT 'claude'")


def upsert_entries(entries: list[TokenEntry]) -> int:
    """Insert new entries, skip duplicates. Returns count of new rows added."""
    if not entries:
        return 0
    with _connect() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO usage
                (session_id, timestamp, model, project,
                 input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e.session_id,
                    e.timestamp.isoformat(),
                    e.model,
                    e.project,
                    e.input_tokens,
                    e.output_tokens,
                    e.cache_write_tokens,
                    e.cache_read_tokens,
                    e.provider,
                )
                for e in entries
            ],
        )
        return conn.total_changes


def sync() -> int:
    """Parse all JSONL files and upsert into SQLite. Returns count of new rows."""
    init_db()
    entries = parse_all()
    return upsert_entries(entries)


def query_range(start: date, end: date) -> list[dict]:
    """Return rows where date(timestamp) is between start and end inclusive."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM usage
            WHERE date(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def query_all() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM usage ORDER BY timestamp").fetchall()
    return [dict(r) for r in rows]


def query_by_project() -> list[dict]:
    """Return per-project aggregates, ordered by total cost descending."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                project,
                model,
                SUM(input_tokens)       AS input_tokens,
                SUM(output_tokens)      AS output_tokens,
                SUM(cache_write_tokens) AS cache_write_tokens,
                SUM(cache_read_tokens)  AS cache_read_tokens,
                MIN(timestamp)          AS first_seen,
                MAX(timestamp)          AS last_seen,
                COUNT(*)                AS entry_count
            FROM usage
            GROUP BY project, model
            ORDER BY project, model
            """
        ).fetchall()
    return [dict(r) for r in rows]


def query_today_totals() -> tuple[int, float] | None:
    """Return (total_tokens, total_cost) for today from SQLite only — no JSONL parsing.

    Returns None if the DB doesn't exist yet (first run, nothing synced).
    """
    db = get_db_path()
    if not db.exists():
        return None

    from .stats import calc_cost

    with _connect() as conn:
        rows = conn.execute(
            "SELECT model, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens "
            "FROM usage WHERE date(timestamp) = date('now', 'localtime')"
        ).fetchall()

    if not rows:
        return None

    total_tokens = 0
    total_cost = 0.0
    for row in rows:
        total_tokens += row[1] + row[2] + row[3] + row[4]
        total_cost += calc_cost(row[0], row[1], row[2], row[3], row[4])

    return total_tokens, total_cost


def get_date_bounds() -> tuple[str | None, str | None]:
    """Return (earliest_date, latest_date) strings from the DB, or (None, None)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT MIN(date(timestamp)), MAX(date(timestamp)) FROM usage"
        ).fetchone()
    return (row[0], row[1]) if row else (None, None)
