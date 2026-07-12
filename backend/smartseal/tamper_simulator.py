"""
RailwayBrain AI - SmartSeal AI Module
------------------------------------------
Freight consignment security simulation, matching the founder's
submitted proposal IS0000000163 (e-Seal replacing lac/lead seals).

Per project spec, this module requires NO real IoT hardware:
- Wagon positions are SIMULATED GPS coordinates moving along
  origin -> destination corridors.
- Tamper events are user-triggered ("SIMULATE TAMPER" button) and
  mapped to the 6 real sensor types named in the proposal (magnetic
  door contact, cable pull-force, 3-axis accelerometer, light sensor,
  seal-replacement detector, signal-jammer detector).
- All simulated data is written to the same SQLite schema a real
  LTE-M/NB-IoT seal fleet would populate, so the dashboard code here
  is the same code that would run against real hardware telemetry -
  only the data source (simulator vs. real seal) changes.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime
from typing import Optional

from backend.database.db_manager import execute, fetch_all, log_event
from backend.database.seed_data import STATIONS

TAMPER_TYPES = {
    "MAGNETIC": "Magnetic door-contact sensor triggered - door opened outside scheduled halt.",
    "CABLE_PULL": "Cable pull-force sensor triggered - seal cable tension anomaly detected.",
    "ACCEL": "3-axis accelerometer flagged abnormal shock/vibration pattern.",
    "LIGHT": "Light sensor triggered - unauthorised container access detected.",
    "REPLACEMENT": "Seal-replacement detector triggered - seal ID mismatch from registered unit.",
    "SIGNAL_JAM": "Signal-jammer detector triggered - GPS/LTE-M signal anomaly (possible jamming).",
}

SEVERITY_BY_TYPE = {
    "MAGNETIC": "HIGH",
    "CABLE_PULL": "HIGH",
    "ACCEL": "MEDIUM",
    "LIGHT": "MEDIUM",
    "REPLACEMENT": "HIGH",
    "SIGNAL_JAM": "HIGH",
}

# Assumed average freight corridor speed, used only to estimate arrival
# time from current simulated GPS position. Documented assumption, not a
# real-time NTES/FOIS feed.
ASSUMED_AVG_SPEED_KMPH = 45.0
_STATION_COORDS = {name: (lat, lon) for name, lat, lon in STATIONS}


def _stable_pseudo_value(seed_text: str, low: float, high: float, bucket_minutes: int = 2) -> float:
    """
    Deterministic-but-slowly-changing pseudo-random value in [low, high],
    derived from a hash of seed_text + a coarse time bucket. Used for
    telemetry fields (speed, signal strength) that should look "live"
    on repeated dashboard refreshes without jumping wildly every second.
    """
    bucket = int(datetime.utcnow().timestamp() // (bucket_minutes * 60))
    h = hashlib.sha256(f"{seed_text}:{bucket}".encode()).hexdigest()
    frac = int(h[:8], 16) / 0xFFFFFFFF
    return round(low + frac * (high - low), 1)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two GPS points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_wagon_telemetry(wagon: dict) -> dict:
    """
    Computes the extra telemetry fields shown on the SmartSeal AI page:
    current speed, signal strength, seal health, last sensor triggered,
    estimated arrival, and a simple risk indicator. All values are
    derived live from the wagon's existing simulated state (position,
    battery, seal_status) plus documented assumptions — nothing here
    claims a live hardware feed.
    """
    wagon_id = wagon["wagon_id"]
    status = wagon["status"]
    seal_status = wagon["seal_status"]
    battery_pct = wagon["battery_pct"]

    # Current speed: 0 if halted/arrived, otherwise a slowly-varying
    # pseudo-random value in a realistic freight range.
    if status == "MOVING":
        current_speed_kmph = _stable_pseudo_value(f"speed:{wagon_id}", 35.0, 78.0)
    else:
        current_speed_kmph = 0.0

    # Signal strength: degraded range if a SIGNAL_JAM-type tamper is
    # currently unresolved on this wagon, otherwise a healthy range.
    latest_tamper = fetch_all(
        "SELECT tamper_type, created_at, resolved FROM tamper_events "
        "WHERE wagon_id = ? ORDER BY created_at DESC LIMIT 1",
        (wagon_id,),
    )
    last_sensor_triggered = latest_tamper[0]["tamper_type"] if latest_tamper else "None"
    jam_active = bool(latest_tamper) and latest_tamper[0]["tamper_type"] == "SIGNAL_JAM" and not latest_tamper[0]["resolved"]
    if jam_active:
        signal_strength_pct = _stable_pseudo_value(f"signal:{wagon_id}", 15.0, 45.0)
    else:
        signal_strength_pct = _stable_pseudo_value(f"signal:{wagon_id}", 65.0, 99.0)

    # Seal health — plain-language summary of seal_status + battery.
    if seal_status == "TAMPERED":
        seal_health = "Compromised"
    elif battery_pct < 20:
        seal_health = "Degraded (Low Battery)"
    else:
        seal_health = "Good"

    # Estimated arrival — great-circle distance to destination station /
    # assumed average speed. Purely illustrative (real routing follows
    # track geometry, not a straight line).
    dest_coords = _STATION_COORDS.get(wagon["destination"])
    if status == "ARRIVED" or dest_coords is None:
        estimated_arrival = "Arrived" if status == "ARRIVED" else "Unknown"
    else:
        dist_km = haversine_km(wagon["lat"], wagon["lon"], dest_coords[0], dest_coords[1])
        hours = dist_km / ASSUMED_AVG_SPEED_KMPH
        if hours < 1:
            estimated_arrival = f"~{int(hours * 60)} min"
        else:
            estimated_arrival = f"~{hours:.1f} hrs"

    # Risk indicator — simple composite of seal status, battery, signal.
    if seal_status == "TAMPERED":
        risk_indicator = "HIGH"
    elif battery_pct < 20 or signal_strength_pct < 40:
        risk_indicator = "MEDIUM"
    else:
        risk_indicator = "LOW"

    simple_recommendations = {
        "HIGH": "Dispatch RPF for physical verification at next scheduled halt.",
        "MEDIUM": "Flag for monitoring; verify at next portal scan.",
        "LOW": "No action needed; routine tracking.",
    }

    return {
        "current_speed_kmph": current_speed_kmph,
        "battery_pct": battery_pct,
        "last_gps_update": wagon["updated_at"],
        "last_sensor_triggered": last_sensor_triggered,
        "seal_health": seal_health,
        "signal_strength_pct": signal_strength_pct,
        "estimated_arrival": estimated_arrival,
        "risk_indicator": risk_indicator,
        "simple_recommendation": simple_recommendations[risk_indicator],
    }


def advance_wagon_positions(step_fraction: float = 0.02) -> None:
    """
    Move every MOVING wagon a small step toward a pseudo-random nearby
    point, simulating a GPS ping. This is a lightweight random-walk -
    good enough for a live-feeling demo map without needing real
    routing data.
    """
    wagons = fetch_all("SELECT wagon_id, lat, lon, status FROM wagons")
    for w in wagons:
        if w["status"] != "MOVING":
            continue
        jitter_lat = random.uniform(-0.03, 0.03) * step_fraction * 10
        jitter_lon = random.uniform(-0.03, 0.03) * step_fraction * 10
        new_lat = w["lat"] + jitter_lat
        new_lon = w["lon"] + jitter_lon
        execute(
            "UPDATE wagons SET lat = ?, lon = ?, updated_at = ? WHERE wagon_id = ?",
            (new_lat, new_lon, datetime.utcnow().isoformat(), w["wagon_id"]),
        )


def simulate_tamper(wagon_id: str, tamper_type: Optional[str] = None) -> dict:
    """
    Trigger a simulated tamper event for a given wagon. If tamper_type
    is not given, one of the 6 sensor types is chosen at random -
    exactly as a real multi-sensor e-Seal unit would report whichever
    sensor tripped first.
    """
    if tamper_type is None:
        tamper_type = random.choice(list(TAMPER_TYPES.keys()))

    severity = SEVERITY_BY_TYPE.get(tamper_type, "MEDIUM")
    description = TAMPER_TYPES.get(tamper_type, "Unknown sensor triggered.")

    wagon_rows = fetch_all("SELECT * FROM wagons WHERE wagon_id = ?", (wagon_id,))
    if not wagon_rows:
        raise ValueError(f"Unknown wagon_id: {wagon_id}")
    wagon = wagon_rows[0]

    recommendation = (
        f"RPF ALERT [{severity}]: {description} Wagon {wagon_id} "
        f"({wagon['commodity']}, {wagon['origin']} -> {wagon['destination']}). "
        f"Dispatch nearest RPF post for physical verification within "
        f"{'15 minutes' if severity == 'HIGH' else '45 minutes'}. "
        f"Freeze consignment tracking status until cleared."
    )

    execute(
        """INSERT INTO tamper_events
           (wagon_id, tamper_type, severity, lat, lon, rpf_recommendation, resolved, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
        (wagon_id, tamper_type, severity, wagon["lat"], wagon["lon"],
         recommendation, datetime.utcnow().isoformat()),
    )
    execute(
        "UPDATE wagons SET seal_status = 'TAMPERED', updated_at = ? WHERE wagon_id = ?",
        (datetime.utcnow().isoformat(), wagon_id),
    )
    log_event("smartseal", "WARNING", f"Simulated tamper on {wagon_id}: {tamper_type}")

    return {
        "wagon_id": wagon_id,
        "tamper_type": tamper_type,
        "severity": severity,
        "description": description,
        "recommendation": recommendation,
    }


def resolve_tamper(event_id: int, wagon_id: str) -> None:
    execute("UPDATE tamper_events SET resolved = 1 WHERE event_id = ?", (event_id,))
    execute(
        "UPDATE wagons SET seal_status = 'SEALED', updated_at = ? WHERE wagon_id = ?",
        (datetime.utcnow().isoformat(), wagon_id),
    )
    log_event("smartseal", "INFO", f"Tamper event {event_id} on {wagon_id} resolved by RPF")
