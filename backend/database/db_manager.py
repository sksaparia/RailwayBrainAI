"""
RailwayBrain AI - Database Manager
------------------------------------
Handles SQLite connection, schema creation, and all CRUD operations
used across RailVision AI, TrackSentinel AI and SmartSeal AI modules.

Design notes:
- SQLite is used because this is a zero-cost MVP demo (per project spec).
- All writes go through parameterised queries (no string-formatted SQL)
  to avoid injection issues even though this is a local demo DB.
- A single shared connection factory is exposed so every module/page
  gets a consistent, thread-safe (check_same_thread=False) connection,
  which Streamlit's rerun model requires.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

logger = logging.getLogger("railwaybrain.db")

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "railwaybrain.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS drivers (
    driver_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    employee_code   TEXT UNIQUE NOT NULL,
    zone            TEXT,
    loco_assigned   TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fatigue_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id       INTEGER,
    source_type     TEXT NOT NULL,        -- 'image' | 'video' | 'webcam'
    source_name     TEXT,
    status          TEXT NOT NULL,        -- SAFE | WARNING | DROWSY
    fatigue_score   REAL NOT NULL,
    attention_score REAL NOT NULL,
    blink_count     INTEGER DEFAULT 0,
    eye_closure_pct REAL DEFAULT 0,
    screenshot_path TEXT,
    recommendation  TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
);

CREATE TABLE IF NOT EXISTS tracks (
    track_id        TEXT PRIMARY KEY,     -- e.g. ECR-DHN-014
    zone            TEXT,
    division        TEXT,
    chainage_km     REAL,
    rail_grade      TEXT,                 -- 90UTS | HH | SH
    installed_year  INTEGER,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inspection_results (
    result_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id            TEXT NOT NULL,
    inspection_date      TEXT NOT NULL,
    crack_length_mm      REAL NOT NULL,
    mgt_cumulative        REAL NOT NULL,    -- million gross tonnes since last
    crack_growth_rate    REAL,             -- da/dN mm per MGT
    risk_score           REAL,             -- 0-100
    remaining_life_mgt   REAL,             -- predicted MGT to critical length
    recommendation       TEXT,
    created_at            TEXT NOT NULL,
    FOREIGN KEY (track_id) REFERENCES tracks(track_id)
);

CREATE TABLE IF NOT EXISTS wagons (
    wagon_id        TEXT PRIMARY KEY,     -- e.g. WG-10234
    wagon_type      TEXT,
    commodity       TEXT,
    origin          TEXT,
    destination     TEXT,
    lat             REAL,
    lon             REAL,
    seal_status     TEXT,                 -- SEALED | TAMPERED | IN_TRANSIT
    battery_pct     REAL,
    status          TEXT,                 -- MOVING | HALTED | ARRIVED
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tamper_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    wagon_id        TEXT NOT NULL,
    tamper_type     TEXT,                 -- MAGNETIC | CABLE_PULL | ACCEL | LIGHT | SIGNAL_JAM
    severity        TEXT,                 -- LOW | MEDIUM | HIGH
    lat             REAL,
    lon             REAL,
    rpf_recommendation TEXT,
    resolved        INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (wagon_id) REFERENCES wagons(wagon_id)
);

CREATE TABLE IF NOT EXISTS system_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    module      TEXT NOT NULL,
    level       TEXT NOT NULL,   -- INFO | WARNING | ERROR
    message     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def init_db() -> None:
    """Create the database file and all tables if they do not exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info("Database initialised at %s", DB_PATH)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def log_event(module: str, level: str, message: str) -> None:
    """Write a row to system_logs. Never raises - logging must not crash the app."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO system_logs (module, level, message, created_at) VALUES (?, ?, ?, ?)",
                (module, level, message, datetime.utcnow().isoformat()),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write system log: %s", exc)


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return the lastrowid."""
    with get_connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return row
