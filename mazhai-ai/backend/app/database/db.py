import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("MAZHAI_DB_PATH", Path(__file__).resolve().parents[3] / "data" / "mazhai.db"))

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
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
