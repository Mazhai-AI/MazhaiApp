import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("MAZHAI_DB_PATH", Path(__file__).resolve().parents[3] / "data" / "mazhai.db"))

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # Reads and writes from the comparison thread pool should wait for each other, not fail.
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def prune_cache(max_age_days=30):
    """Delete api_cache rows older than max_age_days; returns how many were removed.

    Every distinct history date range creates a cache row, so without pruning the table
    only ever grows. Stale rows are still useful as a provider-outage fallback for a while,
    hence the generous default. Observations in rainfall_observations are never pruned.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    with connect() as conn:
        cursor = conn.execute("DELETE FROM api_cache WHERE fetched_at < ?", (cutoff,))
        return cursor.rowcount


def init_db():
    # WAL is persistent for the database file; set it once here rather than on every connection.
    # Some filesystems refuse WAL, in which case SQLite keeps its default journal mode.
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        wal = sqlite3.connect(DB_PATH, timeout=15)
        try:
            wal.execute("PRAGMA journal_mode=WAL")
        finally:
            wal.close()
    except sqlite3.DatabaseError:
        pass
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS rainfall_observations (
            id INTEGER PRIMARY KEY,
            district_id TEXT NOT NULL,
            observed_date TEXT NOT NULL,
            precipitation_mm REAL,
            source TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            UNIQUE(district_id, observed_date, source)
        );
        CREATE INDEX IF NOT EXISTS idx_rainfall_district_date
            ON rainfall_observations(district_id, observed_date);
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ingestion_runs (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            message TEXT
        );
        """)
