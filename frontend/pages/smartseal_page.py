"""RailwayBrain AI - SmartSeal AI page (freight consignment security simulation)."""

from __future__ import annotations

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from backend.database.db_manager import fetch_all
from backend.smartseal.tamper_simulator import (
    TAMPER_TYPES,
    advance_wagon_positions,
    get_wagon_telemetry,
    resolve_tamper,
    simulate_tamper,
)
from frontend.ui_helpers import recommendation_box, render_stat_grid, section_title, status_pill

SEAL_COLOR = {"SEALED": "#16a34a", "TAMPERED": "#dc2626", "IN_TRANSIT": "#2563eb"}


def _build_map(wagons: list) -> folium.Map:
    if wagons:
        center = [wagons[0]["lat"], wagons[0]["lon"]]
    else:
        center = [23.3, 85.3]  # Jharkhand region default

    m = folium.Map(location=center, zoom_start=6, tiles="CartoDB dark_matter")

    for w in wagons:
        color = SEAL_COLOR.get(w["seal_status"], "#2563eb")
        popup = folium.Popup(
            f"<b>{w['wagon_id']}</b><br>{w['commodity']}<br>"
            f"{w['origin']} \u2192 {w['destination']}<br>"
            f"Seal: {w['seal_status']}<br>Battery: {w['battery_pct']}%<br>Status: {w['status']}",
            max_width=250,
        )
        folium.CircleMarker(
            location=[w["lat"], w["lon"]],
            radius=8 if w["seal_status"] == "TAMPERED" else 6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup,
            tooltip=w["wagon_id"],
        ).add_to(m)

    return m


def render() -> None:
    section_title("SmartSeal AI \u2014 Freight Consignment Security", simulated=True)
    st.caption(
        "IoT e-Seal simulation matching proposal IS0000000163. No hardware required — "
        "wagon GPS and tamper events are simulated but flow through the same database "
        "schema and alert pipeline a real LTE-M/NB-IoT seal fleet would use."
    )

    col_refresh, col_advance = st.columns([1, 1])
    with col_refresh:
        if st.button("\U0001F504 Refresh Live Positions"):
            advance_wagon_positions()
            st.rerun()

    wagons = [dict(w) for w in fetch_all("SELECT * FROM wagons ORDER BY wagon_id")]

    map_col, panel_col = st.columns([2, 1])
    with map_col:
        st.markdown('<div class="rb-card">', unsafe_allow_html=True)
        st.markdown('<div class="rb-card-label">Live Wagon Map (GIS)</div>', unsafe_allow_html=True)
        m = _build_map(wagons)
        st_folium(m, use_container_width=True, height=460, key="smartseal_map")
        st.markdown('</div>', unsafe_allow_html=True)

    with panel_col:
        st.markdown('<div class="rb-card">', unsafe_allow_html=True)
        st.markdown('<div class="rb-card-label">Simulate Tamper Event</div>', unsafe_allow_html=True)
        wagon_ids = [w["wagon_id"] for w in wagons]
        target_wagon = st.selectbox("Select wagon", wagon_ids) if wagon_ids else None
        tamper_type = st.selectbox(
            "Sensor type (or Random)",
            ["RANDOM"] + list(TAMPER_TYPES.keys()),
        )
        if target_wagon and st.button("\u26A0\uFE0F SIMULATE TAMPER", type="primary"):
            chosen = None if tamper_type == "RANDOM" else tamper_type
            event = simulate_tamper(target_wagon, chosen)
            st.error(f"TAMPER DETECTED on {event['wagon_id']}: {event['description']}")
            st.markdown(f"**RPF Recommendation:** {event['recommendation']}")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown('<div class="rb-card">', unsafe_allow_html=True)
        st.markdown('<div class="rb-card-label">Fleet Summary</div>', unsafe_allow_html=True)
        total = len(wagons)
        tampered = sum(1 for w in wagons if w["seal_status"] == "TAMPERED")
        moving = sum(1 for w in wagons if w["status"] == "MOVING")
        st.markdown(f"Total wagons: **{total}**")
        st.markdown(f"Currently moving: **{moving}**")
        st.markdown(f"Tampered (unresolved): **{tampered}**")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    section_title("Wagon Telemetry", simulated=True)
    telemetry_wagon = st.selectbox(
        "Select wagon to inspect", [w["wagon_id"] for w in wagons], key="telemetry_wagon"
    ) if wagons else None

    if telemetry_wagon:
        wagon_obj = next(w for w in wagons if w["wagon_id"] == telemetry_wagon)
        t = get_wagon_telemetry(wagon_obj)
        tone = {"LOW": "safe", "MEDIUM": "warn", "HIGH": "danger"}.get(t["risk_indicator"], "")
        render_stat_grid([
            ("Current Speed", f"{t['current_speed_kmph']} km/h", ""),
            ("Battery", f"{t['battery_pct']}%", "warn" if t["battery_pct"] < 20 else ""),
            ("Last GPS Update", t["last_gps_update"][:19].replace("T", " "), ""),
            ("Last Sensor Triggered", t["last_sensor_triggered"], ""),
            ("Seal Health", t["seal_health"], "danger" if t["seal_health"] == "Compromised" else "safe"),
            ("Signal Strength", f"{t['signal_strength_pct']}%", "warn" if t["signal_strength_pct"] < 40 else ""),
            ("Estimated Arrival", t["estimated_arrival"], ""),
            ("Risk Indicator", t["risk_indicator"], tone),
        ])
        recommendation_box(t["simple_recommendation"], level=tone if tone else "info",
                            label="RPF Recommendation")

    st.markdown("<br/>", unsafe_allow_html=True)
    section_title("Tamper Event Timeline")

    events = fetch_all(
        "SELECT te.event_id, te.wagon_id, te.tamper_type, te.severity, te.resolved, "
        "te.rpf_recommendation, te.created_at, w.commodity "
        "FROM tamper_events te JOIN wagons w ON w.wagon_id = te.wagon_id "
        "ORDER BY te.created_at DESC LIMIT 50"
    )
    if not events:
        st.info("No tamper events yet. Trigger one above to see the RPF alert workflow.")
    else:
        for e in events:
            status_txt = "RESOLVED" if e["resolved"] else "OPEN"
            cols = st.columns([2, 2, 2, 2, 1])
            cols[0].markdown(f"**{e['wagon_id']}** ({e['commodity']})")
            cols[1].markdown(e["tamper_type"])
            cols[2].markdown(status_pill(e["severity"]), unsafe_allow_html=True)
            cols[3].markdown(status_pill("SAFE" if e["resolved"] else "DROWSY") + f" {status_txt}",
                              unsafe_allow_html=True)
            if not e["resolved"]:
                if cols[4].button("Resolve", key=f"resolve_{e['event_id']}"):
                    resolve_tamper(e["event_id"], e["wagon_id"])
                    st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)
    all_wagons_df = pd.DataFrame(wagons)
    if not all_wagons_df.empty:
        section_title("All Wagons")
        all_wagons_df["risk_indicator"] = [
            get_wagon_telemetry(w)["risk_indicator"] for w in wagons
        ]
        st.dataframe(
            all_wagons_df[["wagon_id", "wagon_type", "commodity", "origin", "destination",
                            "seal_status", "battery_pct", "status", "risk_indicator", "updated_at"]],
            width="stretch", hide_index=True,
        )
