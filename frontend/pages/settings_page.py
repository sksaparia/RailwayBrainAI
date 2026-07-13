"""RailwayBrain AI - Settings page."""

from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st

from backend.database.db_manager import DB_PATH, execute, fetch_all
from backend.database.seed_data import seed_all
from backend.tracksentinel.crack_growth_model import analyse_uploaded_csv
from frontend.ui_helpers import render_stat_grid, section_title

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data",
    "sample_usfd_inspection_data.csv",
)

ALL_TABLES = ["drivers", "fatigue_events", "tracks", "inspection_results",
              "wagons", "tamper_events", "system_logs"]


def render() -> None:
    section_title("Settings")

    # --- Database Statistics -------------------------------------------------
    st.markdown("**Database Statistics**")
    db_size_kb = round(os.path.getsize(DB_PATH) / 1024, 1) if os.path.exists(DB_PATH) else 0
    counts = {}
    for table in ALL_TABLES:
        row = fetch_all(f"SELECT COUNT(*) c FROM {table}")
        counts[table] = row[0]["c"] if row else 0

    render_stat_grid([
        ("Database Size", f"{db_size_kb} KB", ""),
        ("Total Tables", str(len(ALL_TABLES)), ""),
        ("Total Records", str(sum(counts.values())), "accent"),
    ])
    st.table({"Table": list(counts.keys()), "Rows": list(counts.values())})
    st.caption(f"Path: `{DB_PATH}`")

    st.divider()
    st.markdown("**Data Management**")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("Reset Demo")
        if st.button("\U0001F504 Reset Demo", type="secondary"):
            for table in ALL_TABLES:
                execute(f"DELETE FROM {table}")
            seed_all()
            st.success("Demo reset to a fresh baseline (drivers, tracks, wagons reseeded; all events cleared).")
            st.rerun()

    with col2:
        st.caption("Backup & Restore Database")
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button(
                "\U0001F4E5 Download Backup (.db)",
                db_bytes,
                file_name="railwaybrain.db",
                mime="application/octet-stream",
            )
        else:
            st.caption("No database file found yet.")

        # Restore: upload a previously-downloaded .db to survive Streamlit
        # Cloud restarts (which wipe the ephemeral filesystem).
        restore_file = st.file_uploader(
            "Restore from backup (.db)", type=["db"], key="db_restore",
            label_visibility="collapsed",
        )
        if restore_file is not None:
            if st.button("\u267B\uFE0F Restore This Backup", key="do_restore"):
                try:
                    import sqlite3
                    data = restore_file.read()
                    # Validate it's a real SQLite file before overwriting
                    if not data[:16].startswith(b"SQLite format 3"):
                        st.error("That file is not a valid SQLite database.")
                    else:
                        with open(DB_PATH, "wb") as f:
                            f.write(data)
                        # Quick integrity check
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute("PRAGMA integrity_check;")
                        conn.close()
                        st.success("Database restored from backup. Reloading...")
                        st.session_state.pop("rb_bootstrapped", None)
                        st.rerun()
                except Exception as exc:
                    st.error(f"Restore failed: {exc}")

    with col3:
        st.caption("Import Sample Data")
        if st.button("\U0001F4C5 Import Sample USFD Data"):
            try:
                sample_df = pd.read_csv(SAMPLE_CSV_PATH)
                results_df = analyse_uploaded_csv(sample_df, rail_grade="90UTS")
                from datetime import datetime
                for _, row in results_df.iterrows():
                    existing_track = fetch_all(
                        "SELECT 1 FROM tracks WHERE track_id = ?", (row["track_id"],)
                    )
                    if not existing_track:
                        execute(
                            """INSERT INTO tracks (track_id, zone, division, chainage_km,
                               rail_grade, installed_year, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (row["track_id"], "SAMPLE", "Imported", 0.0, "90UTS", 2020,
                             datetime.utcnow().isoformat()),
                        )
                    execute(
                        """INSERT INTO inspection_results
                           (track_id, inspection_date, crack_length_mm, mgt_cumulative,
                            crack_growth_rate, risk_score, remaining_life_mgt, recommendation, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (row["track_id"], datetime.utcnow().strftime("%Y-%m-%d"), 0.0, 0.0,
                         row["growth_rate_mm_per_mgt"], row["risk_score"], row["remaining_life_mgt"],
                         row["recommendation"], datetime.utcnow().isoformat()),
                    )
                st.success(f"Imported {len(results_df)} sample inspection result(s) from bundled sample data.")
                st.rerun()
            except FileNotFoundError:
                st.error("Bundled sample_data/sample_usfd_inspection_data.csv not found.")
            except ValueError as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("**Detection Thresholds (RailVision AI)**")
    st.caption("These mirror the constants defined in `backend/railvision/fatigue_engine.py`. "
               "Editable here for demo purposes; a production build would persist this to config.")
    st.slider("Eye-closure % → WARNING", 0, 100, 35, disabled=True)
    st.slider("Eye-closure % → DROWSY", 0, 100, 60, disabled=True)

    st.divider()
    st.markdown("**Risk Thresholds (TrackSentinel AI)**")
    st.slider("Risk score → MEDIUM band", 0, 100, 40, disabled=True)
    st.slider("Risk score → HIGH band", 0, 100, 70, disabled=True)

    st.divider()
    st.markdown("**About this build**")
    st.code(
        "Tech stack: Python, Streamlit, OpenCV, Plotly, Pandas, NumPy, SQLite, Folium (Leaflet)\n"
        "Mode: Local / zero-cost demo build\n"
        "All 'simulated' badges in the app mark data that is synthetically generated,\n"
        "not sourced from a live Indian Railways feed.",
        language="text",
    )
