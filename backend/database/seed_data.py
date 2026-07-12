"""
RailwayBrain AI - Seed Data Generator
----------------------------------------
Populates the SQLite database with SIMULATED demo data so the app is
immediately explorable without requiring a real Railway data feed.

*** ALL DATA GENERATED HERE IS CLEARLY LABELLED SIMULATED DATA. ***
No real Indian Railways operational data is used anywhere in this repo.
Station/route names are illustrative and drawn from public geography
(East Central Railway / Jharkhand corridor, matching the founder's
submitted proposal context), not from any live Railway system.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from backend.database.db_manager import execute, fetch_one, get_connection, log_event

random.seed(42)  # deterministic demo data across runs

ZONES = ["ECR", "SER", "ER", "NR", "WR"]
DIVISIONS = {
    "ECR": ["Dhanbad", "Danapur", "Sonpur", "Samastipur"],
    "SER": ["Kharagpur", "Chakradharpur", "Adra"],
    "ER": ["Howrah", "Sealdah", "Asansol"],
    "NR": ["Delhi", "Ambala", "Lucknow"],
    "WR": ["Mumbai Central", "Ratlam", "Vadodara"],
}
RAIL_GRADES = ["90UTS", "HH", "SH"]

DRIVER_NAMES = [
    "R. Kumar", "S. Mahato", "A. Singh", "V. Prasad", "B. Oraon",
    "M. Tiwari", "D. Yadav", "K. Verma", "P. Soren", "N. Sharma",
    "J. Das", "T. Mishra",
]

COMMODITIES = ["Iron Ore", "Steel Coils", "Coal", "Cement", "Foodgrains", "Containers", "Limestone"]
STATIONS = [
    ("Jamshedpur", 22.8046, 86.2029),
    ("Tatanagar", 22.7925, 86.1844),
    ("Dhanbad", 23.7957, 86.4304),
    ("Bokaro", 23.6693, 86.1511),
    ("Ranchi", 23.3441, 85.3096),
    ("Adra", 23.4919, 86.6717),
    ("Kharagpur", 22.3460, 87.2320),
    ("Howrah", 22.5958, 88.2636),
    ("Rourkela", 22.2604, 84.8536),
    ("Chakradharpur", 22.6981, 85.6297),
]


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def seed_drivers(n: int = 12) -> None:
    existing = fetch_one("SELECT COUNT(*) as c FROM drivers")
    if existing and existing["c"] > 0:
        return
    for i, name in enumerate(DRIVER_NAMES[:n]):
        zone = random.choice(ZONES)
        execute(
            """INSERT INTO drivers (name, employee_code, zone, loco_assigned, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (name, f"EMP{1000+i}", zone, f"WAG-{30000+i*7}", _now_iso()),
        )
    log_event("seed_data", "INFO", f"Seeded {n} drivers (simulated)")


def seed_tracks(n: int = 20) -> None:
    existing = fetch_one("SELECT COUNT(*) as c FROM tracks")
    if existing and existing["c"] > 0:
        return
    for i in range(n):
        zone = random.choice(ZONES)
        division = random.choice(DIVISIONS[zone])
        track_id = f"{zone}-{division[:3].upper()}-{100+i}"
        execute(
            """INSERT INTO tracks (track_id, zone, division, chainage_km, rail_grade, installed_year, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                track_id, zone, division,
                round(random.uniform(5, 480), 2),
                random.choice(RAIL_GRADES),
                random.randint(2005, 2022),
                _now_iso(),
            ),
        )
    log_event("seed_data", "INFO", f"Seeded {n} track segments (simulated)")


def seed_wagons(n: int = 15) -> None:
    existing = fetch_one("SELECT COUNT(*) as c FROM wagons")
    if existing and existing["c"] > 0:
        return
    for i in range(n):
        origin, olat, olon = random.choice(STATIONS)
        dest, dlat, dlon = random.choice([s for s in STATIONS if s[0] != origin])
        # place the wagon somewhere along the straight line origin->dest
        t = random.uniform(0.05, 0.95)
        lat = olat + (dlat - olat) * t
        lon = olon + (dlon - olon) * t
        execute(
            """INSERT INTO wagons (wagon_id, wagon_type, commodity, origin, destination,
               lat, lon, seal_status, battery_pct, status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"WG-{10000+i}",
                random.choice(["BOXN", "BCNA", "BOBRN", "BLC Container"]),
                random.choice(COMMODITIES),
                origin, dest, lat, lon,
                "SEALED",
                round(random.uniform(55, 100), 1),
                random.choice(["MOVING", "MOVING", "HALTED"]),
                _now_iso(),
            ),
        )
    log_event("seed_data", "INFO", f"Seeded {n} wagons (simulated GPS)")


def seed_all() -> None:
    seed_drivers()
    seed_tracks()
    seed_wagons()
