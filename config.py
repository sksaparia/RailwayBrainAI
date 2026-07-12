"""
RailwayBrain AI - Central Configuration
--------------------------------------------
Single place to tune thresholds and paths without hunting through
module files. Imported by backend modules where relevant.
"""

from __future__ import annotations

import os

APP_NAME = "RailwayBrain AI"
APP_TAGLINE = "India's First Unified AI Brain for Indian Railways"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(ROOT_DIR, "backend", "database")
SCREENSHOTS_DIR = os.path.join(ROOT_DIR, "screenshots")

# --- RailVision AI thresholds -------------------------------------------------
EYE_CLOSURE_WARNING_PCT = 35.0
EYE_CLOSURE_DROWSY_PCT = 60.0
VIDEO_SAMPLE_EVERY_N_FRAMES = 5
VIDEO_MAX_FRAMES = 150

# --- TrackSentinel AI thresholds ----------------------------------------------
RISK_BAND_HIGH = 70.0
RISK_BAND_MEDIUM = 40.0

# --- SmartSeal AI ---------------------------------------------------------------
WAGON_POSITION_JITTER = 0.02

# --- Theme ------------------------------------------------------------------------
THEME_COLORS = {
    "background": "#0a1120",
    "panel": "#111c33",
    "orange_accent": "#ff7a1a",
    "blue_accent": "#3fa9f5",
    "safe": "#2ecc71",
    "warn": "#f5b942",
    "danger": "#ff4d4f",
}
