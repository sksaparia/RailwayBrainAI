from __future__ import annotations
import os
from datetime import datetime
from typing import Optional
import streamlit as st

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
CSS_PATH = os.path.join(APP_ROOT, "frontend", "css", "theme.css")
LOGO_PATH = os.path.join(APP_ROOT, "assets", "logos", "railwaybrain_logo.svg")
FOUNDER_NAME = "Sachin Saparia"
FOOTER_ORG = "Vande Bharatam Innovation Challenge - Adani Group"


def load_css() -> None:
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_logo_svg() -> str:
    with open(LOGO_PATH, "r", encoding="utf-8") as f:
        return f.read()


def kpi_card(label: str, value: str, sub: str = "", accent: bool = False) -> str:
    value_cls = "rb-card-value accent" if accent else "rb-card-value"
    return (
        '<div class="rb-card">'
        '<div class="rb-card-label">' + label + "</div>"
        '<div class="' + value_cls + '">' + value + "</div>"
        '<div class="rb-card-sub">' + sub + "</div>"
        "</div>"
    )


def render_kpi_row(cards: list) -> None:
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
    return '<span class="rb-pill ' + cls + '">' + status + "</span>"


def sim_badge(text: str = "SIMULATED DATA") -> str:
    return '<span class="rb-sim-badge">' + text + "</span>"


def section_title(text: str, simulated: bool = False) -> None:
    badge = sim_badge() if simulated else ""
    st.markdown('<div class="rb-section-title">' + text + " " + badge + "</div>", unsafe_allow_html=True)


def brand_header(subtitle: str = "Unified AI Platform for Indian Railways") -> None:
    logo_svg = load_logo_svg()
    html = (
        '<div style="display:flex; align-items:center; gap:14px; margin-bottom: 6px;">'
        '<div style="width:52px; height:52px;" class="rb-logo-wrap">' + logo_svg + "</div>"
        "<div>"
        '<div class="rb-brand-title">RAILWAYBRAIN<span class="accent"> AI</span></div>'
        '<div class="rb-brand-sub">' + subtitle + "</div>"
        "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def page_meta_bar(module_name: str, description: str) -> None:
    now = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    html = (
        '<div class="rb-meta-bar">'
        '<div class="rb-meta-left">'
        '<span class="rb-meta-module">' + module_name + "</span>"
        '<span class="rb-meta-desc">' + description + "</span>"
        "</div>"
        '<div class="rb-meta-time">\U0001f551 ' + now + "</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def footer() -> None:
    year = str(datetime.now().year)
    html = (
        '<div class="rb-footer">'
        '<div class="rb-footer-left">'
        "<b>RailwayBrain AI</b> &nbsp;&bull;&nbsp; " + FOOTER_ORG +
        "</div>"
        '<div class="rb-footer-right">'
        "Founder: <b>" + FOUNDER_NAME + "</b> &nbsp;&bull;&nbsp; &copy; " + year +
        "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_stat_grid(items: list) -> None:
    cols = st.columns(min(len(items), 4))
    for i, (label, value, _tone) in enumerate(items):
        with cols[i % 4]:
            st.metric(label=label, value=value)


def recommendation_box(text: str, level: str = "info", label: str = "AI Recommendation") -> None:
    if level == "danger":
        st.error("**" + label + ":** " + text)
    elif level == "safe":
        st.success("**" + label + ":** " + text)
    else:
        st.info("**" + label + ":** " + text)


def mini_timeline(items: list) -> None:
    if not items:
        st.info("No recent events yet.")
        return
    for t, m, txt in items:
        st.markdown("`" + t + "` &nbsp; **" + m + "** &nbsp; " + txt, unsafe_allow_html=True)


def gauge_chart(value: float, title: str, color: str = "#ff7a1a", max_value: float = 100):
    import plotly.graph_objects as go
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": "#e7ecf5", "size": 13}},
        number={"font": {"color": color}},
        gauge={
            "axis": {"range": [0, max_value]},
            "bar": {"color": color},
            "bgcolor": "#16223f",
        },
    ))
    fig.update_layout(
        height=190, margin=dict(l=15, r=15, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf5",
    )
    return fig
