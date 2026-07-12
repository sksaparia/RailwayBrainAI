"""RailwayBrain AI - Dashboard page."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psutil
import streamlit as st

from backend.database.db_manager import fetch_all
from frontend.ui_helpers import (
    mini_timeline,
    recommendation_box,
    render_kpi_row,
    render_stat_grid,
    section_title,
    status_pill,
)


def _count(query: str) -> int:
    rows = fetch_all(query)
    return rows[0][0] if rows else 0


def _last_time(query: str) -> Optional[str]:
    rows = fetch_all(query)
    val = rows[0][0] if rows else None
    return val


def _time_ago(iso_ts: Optional[str]) -> str:
    if not iso_ts:
        return "No data yet"
    try:
        then = datetime.fromisoformat(iso_ts)
    except ValueError:
        return iso_ts[:19]
    delta = datetime.utcnow() - then
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "Just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _compute_ai_health_score() -> tuple[int, str, str]:
    """
    A simple, honest composite health score (0-100) derived from live
    counts already on this dashboard — not a black-box AI confidence
    number. Penalises unresolved high-severity tamper events, high-risk
    tracks, and today's drowsy-driver events.
    Returns (score, status_label, tone).
    """
    unresolved_high_tamper = _count(
        "SELECT COUNT(*) FROM tamper_events WHERE resolved = 0 AND severity = 'HIGH'"
    )
    high_risk_tracks = _count("SELECT COUNT(*) FROM inspection_results WHERE risk_score >= 70")
    today = datetime.utcnow().date().isoformat()
    drowsy_today = _count(
        f"SELECT COUNT(*) FROM fatigue_events WHERE status = 'DROWSY' AND date(created_at) = date('{today}')"
    )

    score = 100
    score -= min(40, unresolved_high_tamper * 15)
    score -= min(30, high_risk_tracks * 6)
    score -= min(30, drowsy_today * 10)
    score = max(0, score)

    if score >= 80:
        return score, "All Systems Operational", "safe"
    if score >= 50:
        return score, "Attention Required", "warn"
    return score, "Critical \u2014 Immediate Review Needed", "danger"


def _top_recommendation() -> tuple[str, str]:
    """Picks the single most urgent recommendation across all three
    modules to surface on the dashboard. Returns (text, level)."""
    high_tamper = fetch_all(
        "SELECT rpf_recommendation FROM tamper_events WHERE resolved = 0 AND severity = 'HIGH' "
        "ORDER BY created_at DESC LIMIT 1"
    )
    if high_tamper:
        return high_tamper[0]["rpf_recommendation"], "danger"

    high_risk_track = fetch_all(
        "SELECT recommendation FROM inspection_results WHERE risk_score >= 70 "
        "ORDER BY created_at DESC LIMIT 1"
    )
    if high_risk_track:
        return high_risk_track[0]["recommendation"], "danger"

    drowsy = fetch_all(
        "SELECT recommendation FROM fatigue_events WHERE status = 'DROWSY' "
        "ORDER BY created_at DESC LIMIT 1"
    )
    if drowsy:
        return drowsy[0]["recommendation"], "danger"

    medium_tamper = fetch_all(
        "SELECT rpf_recommendation FROM tamper_events WHERE resolved = 0 "
        "ORDER BY created_at DESC LIMIT 1"
    )
    if medium_tamper:
        return medium_tamper[0]["rpf_recommendation"], "info"

    return (
        "All modules within normal operating range. No immediate action required. "
        "Continue standard monitoring.",
        "safe",
    )


def render() -> None:
    section_title("Enterprise Operations Dashboard")

    today = datetime.utcnow().date().isoformat()

    total_alerts_today = _count(
        f"SELECT COUNT(*) FROM fatigue_events WHERE date(created_at) = date('{today}') "
        f"AND status IN ('WARNING','DROWSY')"
    ) + _count(
        f"SELECT COUNT(*) FROM tamper_events WHERE date(created_at) = date('{today}')"
    )
    active_drivers = _count("SELECT COUNT(*) FROM drivers")
    protected_wagons = _count("SELECT COUNT(*) FROM wagons WHERE seal_status != 'TAMPERED'")
    high_risk_tracks = _count(
        "SELECT COUNT(*) FROM inspection_results WHERE risk_score >= 70"
    )

    render_kpi_row([
        ("Today's Alerts", str(total_alerts_today), "Fatigue + tamper events", True),
        ("Active Drivers", str(active_drivers), "Monitored by RailVision AI", False),
        ("Protected Wagons", str(protected_wagons), "SmartSeal fleet, sealed status", False),
        ("High-Risk Tracks", str(high_risk_tracks), "Risk score \u2265 70", False),
    ])

    # --- AI Health Score, System Status & module freshness ---------------
    health_score, health_label, health_tone = _compute_ai_health_score()
    last_fatigue = _last_time("SELECT MAX(created_at) FROM fatigue_events")
    last_tamper = _last_time("SELECT MAX(created_at) FROM tamper_events")
    last_track = _last_time("SELECT MAX(created_at) FROM inspection_results")
    candidates = [t for t in [last_fatigue, last_tamper, last_track] if t]
    last_analysis = max(candidates) if candidates else None

    st.markdown("<br/>", unsafe_allow_html=True)
    render_stat_grid([
        ("AI Health Score", f"{health_score}/100", health_tone),
        ("System Status", health_label, health_tone),
        ("Last Analysis Time", _time_ago(last_analysis), ""),
        ("Last Fatigue Detection", _time_ago(last_fatigue), ""),
        ("Last Tamper Detection", _time_ago(last_tamper), ""),
        ("Last Track Analysis", _time_ago(last_track), ""),
    ])

    reco_text, reco_level = _top_recommendation()
    recommendation_box(reco_text, level=reco_level)

    st.markdown("<br/>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory().percent
        st.markdown('<div class="rb-card">', unsafe_allow_html=True)
        st.markdown('<div class="rb-card-label">AI Engine Status</div>', unsafe_allow_html=True)
        gauge1, gauge2 = st.columns(2)
        with gauge1:
            fig_cpu = go.Figure(go.Indicator(
                mode="gauge+number", value=cpu,
                title={"text": "CPU %", "font": {"color": "#e7ecf5", "size": 14}},
                number={"font": {"color": "#ff7a1a"}},
                gauge={"axis": {"range": [0, 100], "tickcolor": "#9aa8c2"},
                       "bar": {"color": "#ff7a1a"},
                       "bgcolor": "#16223f",
                       "borderwidth": 1, "bordercolor": "#22304f"},
            ))
            fig_cpu.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10),
                                   paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf5")
            st.plotly_chart(fig_cpu, width="stretch")
        with gauge2:
            fig_mem = go.Figure(go.Indicator(
                mode="gauge+number", value=mem,
                title={"text": "Memory %", "font": {"color": "#e7ecf5", "size": 14}},
                number={"font": {"color": "#3fa9f5"}},
                gauge={"axis": {"range": [0, 100], "tickcolor": "#9aa8c2"},
                       "bar": {"color": "#3fa9f5"},
                       "bgcolor": "#16223f",
                       "borderwidth": 1, "bordercolor": "#22304f"},
            ))
            fig_mem.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10),
                                   paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf5")
            st.plotly_chart(fig_mem, width="stretch")
        st.markdown(
            f'<div class="rb-card-sub">Live server time (UTC): '
            f'{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="rb-card">', unsafe_allow_html=True)
        st.markdown('<div class="rb-card-label">Alert Timeline (Last 14 Days)</div>', unsafe_allow_html=True)
        days = [(datetime.utcnow().date() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        fatigue_rows = fetch_all(
            "SELECT date(created_at) d, COUNT(*) c FROM fatigue_events "
            "WHERE status IN ('WARNING','DROWSY') GROUP BY d"
        )
        tamper_rows = fetch_all("SELECT date(created_at) d, COUNT(*) c FROM tamper_events GROUP BY d")
        fatigue_map = {r["d"]: r["c"] for r in fatigue_rows}
        tamper_map = {r["d"]: r["c"] for r in tamper_rows}
        df = pd.DataFrame({
            "date": days,
            "RailVision Alerts": [fatigue_map.get(d, 0) for d in days],
            "SmartSeal Alerts": [tamper_map.get(d, 0) for d in days],
        })
        fig = px.line(df, x="date", y=["RailVision Alerts", "SmartSeal Alerts"],
                       color_discrete_sequence=["#ff7a1a", "#3fa9f5"])
        fig.update_layout(
            height=250, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e7ecf5", legend=dict(orientation="h", y=1.15),
            xaxis=dict(gridcolor="#22304f"), yaxis=dict(gridcolor="#22304f"),
        )
        st.plotly_chart(fig, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    recent_fatigue = fetch_all(
        "SELECT created_at, status, fatigue_score FROM fatigue_events ORDER BY created_at DESC LIMIT 5"
    )
    recent_tamper = fetch_all(
        "SELECT created_at, wagon_id, tamper_type, severity FROM tamper_events ORDER BY created_at DESC LIMIT 5"
    )
    recent_inspection = fetch_all(
        "SELECT created_at, track_id, risk_score, recommendation FROM inspection_results "
        "ORDER BY created_at DESC LIMIT 5"
    )

    section_title("Today's Summary")
    fatigue_today = _count(
        f"SELECT COUNT(*) FROM fatigue_events WHERE date(created_at) = date('{today}')"
    )
    tamper_today = _count(
        f"SELECT COUNT(*) FROM tamper_events WHERE date(created_at) = date('{today}')"
    )
    tracks_today = _count(
        f"SELECT COUNT(*) FROM inspection_results WHERE date(created_at) = date('{today}')"
    )
    render_stat_grid([
        ("Fatigue Checks Today", str(fatigue_today), ""),
        ("Tamper Events Today", str(tamper_today), ""),
        ("Track Analyses Today", str(tracks_today), ""),
        ("Total Events Today", str(fatigue_today + tamper_today + tracks_today), "accent"),
    ])

    section_title("Event Timeline")
    merged_events: list[tuple[str, str, str]] = []
    for r in recent_fatigue:
        merged_events.append((r["created_at"][:19], "RailVision", f"Driver status {r['status']} (score {r['fatigue_score']})"))
    for r in recent_tamper:
        merged_events.append((r["created_at"][:19], "SmartSeal", f"{r['tamper_type']} on {r['wagon_id']} ({r['severity']})"))
    for r in recent_inspection:
        merged_events.append((r["created_at"][:19], "TrackSentinel", f"{r['track_id']} risk score {r['risk_score']}"))
    merged_events.sort(key=lambda x: x[0], reverse=True)
    mini_timeline(merged_events[:8])

    st.markdown("<br/>", unsafe_allow_html=True)
    section_title("Recent Events Across All Modules")

    tab1, tab2, tab3 = st.tabs(["\U0001F441\uFE0F RailVision", "\U0001F512 SmartSeal", "\U0001F6E4\uFE0F TrackSentinel"])
    with tab1:
        if recent_fatigue:
            for r in recent_fatigue:
                st.markdown(
                    f"{r['created_at'][:19]} &nbsp; {status_pill(r['status'])} "
                    f"&nbsp; Fatigue score: **{r['fatigue_score']}**",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No fatigue events yet. Try RailVision AI \u2192 upload an image/video.")
    with tab2:
        if recent_tamper:
            for r in recent_tamper:
                st.markdown(
                    f"{r['created_at'][:19]} &nbsp; **{r['wagon_id']}** &nbsp; "
                    f"{r['tamper_type']} &nbsp; {status_pill(r['severity'])}",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No tamper events yet. Try SmartSeal AI \u2192 Simulate Tamper.")
    with tab3:
        if recent_inspection:
            for r in recent_inspection:
                st.markdown(
                    f"{r['created_at'][:19]} &nbsp; **{r['track_id']}** &nbsp; "
                    f"Risk score: **{r['risk_score']}**",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No inspection results yet. Try TrackSentinel AI \u2192 Analyse Track.")
