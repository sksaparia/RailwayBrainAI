"""
RailwayBrain AI - Shared UI Helpers
---------------------------------------
Small reusable rendering functions so every page shares the same
enterprise look (KPI cards, status pills, section headers, simulation
badges) without duplicating HTML/CSS across modules.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import streamlit as st

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
CSS_PATH = os.path.join(APP_ROOT, "frontend", "css", "theme.css")
LOGO_PATH = os.path.join(APP_ROOT, "assets", "logos", "railwaybrain_logo.svg")

FOUNDER_NAME = "Sachin Saparia"
FOOTER_ORG = "Vande Bharatam Innovation Challenge \u2014 Adani Group"


def load_css() -> None:
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_logo_svg() -> str:
    with open(LOGO_PATH, "r", encoding="utf-8") as f:
        return f.read()


def kpi_card(label: str, value: str, sub: str = "", accent: bool = False) -> str:
    value_cls = "rb-card-value accent" if accent else "rb-card-value"
    return f"""
    <div class="rb-card">
        <div class="rb-card-label">{label}</div>
        <div class="{value_cls}">{value}</div>
        <div class="rb-card-sub">{sub}</div>
    </div>
    """


def render_kpi_row(cards: list[tuple[str, str, str, bool]]) -> None:
    cols = st.columns(len(cards))
    for col, (label, value, sub, accent) in zip(cols, cards):
        with col:
            st.markdown(kpi_card(label, value, sub, accent), unsafe_allow_html=True)


def status_pill(status: str) -> str:
    mapping = {
        "SAFE": "rb-pill-safe", "LOW": "rb-pill-low",
        "WARNING": "rb-pill-warn", "MEDIUM": "rb-pill-medium",
        "DROWSY": "rb-pill-drowsy", "HIGH": "rb-pill-high",
        "UNKNOWN": "rb-pill-medium",
    }
    cls = mapping.get(status.upper(), "rb-pill-medium")
    return f'<span class="rb-pill {cls}">{status}</span>'

def sim_badge(text: str = "SIMULATED DATA") -> str:
    return f'<span class="rb-sim-badge">{text}</span>'


def section_title(text: str, simulated: bool = False) -> None:
    badge = sim_badge() if simulated else ""
    st.markdown(f'<div class="rb-section-title">{text} {badge}</div>', unsafe_allow_html=True)


def brand_header(subtitle: str = "Unified AI Platform for Indian Railways") -> None:
    logo_svg = load_logo_svg()
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:14px; margin-bottom: 6px;">
            <div style="width:52px; height:52px;" class="rb-logo-wrap">{logo_svg}</div>
            <div>
                <div class="rb-brand-title">RAILWAYBRAIN<span class="accent"> AI</span></div>
                <div class="rb-brand-sub">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------ #
# Polish-pass helpers: meta bar, footer, stat tiles, recommendation
# box, mini timeline, compact gauge. Used across all pages.
# ------------------------------------------------------------------ #

def page_meta_bar(module_name: str, description: str) -> None:
    """Small bar shown at the top of every page: module name, one-line
    description, and the current time — per-page context at a glance."""
    now = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    st.markdown(
        f"""
        <div class="rb-meta-bar">
            <div class="rb-meta-left">
                <span class="rb-meta-module">{module_name}</span>
                <span class="rb-meta-desc">{description}</span>
            </div>
            <div class="rb-meta-time">\U0001F551 {now}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    """Professional footer shown once at the bottom of every page."""
    year = datetime.now().year
    st.markdown(
        f"""
        <div class="rb-footer">
            <div class="rb-footer-left">
                <b>RailwayBrain AI</b> &nbsp;\u2022&nbsp; {FOOTER_ORG}
            </div>
            <div class="rb-footer-right">
                Founder: <b>{FOUNDER_NAME}</b> &nbsp;\u2022&nbsp; \u00A9 {year}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_tile(label: str, value: str, tone: str = "") -> str:
    """A small, compact stat tile — used for secondary metrics that
    don't need the full-size KPI card treatment (e.g. Blink Count,
    Confidence Score, Battery %)."""
    cls = f"rb-stat-tile-value {tone}".strip()
    return f"""
    <div class="rb-stat-tile">
        <div class="rb-stat-tile-label">{label}</div>
        <div class="{cls}">{value}</div>
    </div>
    """


def render_stat_grid(items: list[tuple[str, str, str]]) -> None:
    """items: list of (label, value, tone) where tone is one of
    '', 'accent', 'safe', 'warn', 'danger'."""
    html = '<div class="rb-stat-grid">' + "".join(
        stat_tile(label, value, tone) for label, value, tone in items
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def recommendation_box(text: str, level: str = "info", label: str = "AI Recommendation") -> None:
    """level: 'info' (orange, default) | 'safe' | 'danger'."""
    icon = {"safe": "\u2705", "danger": "\u26A0\uFE0F", "info": "\U0001F4A1"}.get(level, "\U0001F4A1")
    cls = "" if level == "info" else level
    st.markdown(
        f"""
        <div class="rb-reco-box {cls}">
            <div class="rb-reco-icon">{icon}</div>
            <div>
                <div class="rb-reco-label">{label}</div>
                <div class="rb-reco-text">{text}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_timeline(items: list[tuple[str, str, str]]) -> None:
    """items: list of (time_str, module_label, text), most recent first."""
    if not items:
        st.info("No recent events yet.")
        return
    rows = "".join(
        f"""<div class="rb-timeline-item">
                <span class="rb-timeline-time">{t}</span>
                <span class="rb-timeline-module">{m}</span>
                <span class="rb-timeline-text">{txt}</span>
            </div>"""
        for t, m, txt in items
    )
    st.markdown(f'<div class="rb-timeline">{rows}</div>', unsafe_allow_html=True)


def gauge_chart(value: float, title: str, color: str = "#ea580c", max_value: float = 100):
    """Returns a small Plotly gauge figure themed to match the app,
    wrapped by the caller in st.plotly_chart(). Kept intentionally
    simple — a single needle gauge, no extra chrome."""
    import plotly.graph_objects as go

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": "#1e293b", "size": 13}},
        number={"font": {"color": color}, "suffix": ""},
        gauge={
            "axis": {"range": [0, max_value], "tickcolor": "#64748b"},
            "bar": {"color": color},
            "bgcolor": "#ffffff",
            "borderwidth": 1,
            "bordercolor": "#dbe3ec",
        },
    ))
    fig.update_layout(
        height=190, margin=dict(l=15, r=15, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font_color="#1e293b",
    )
    return fig
