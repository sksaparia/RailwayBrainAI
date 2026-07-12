from _future_ import annotations
import os
from datetime import datetime
from typing import Optional
import streamlit as st

APP_ROOT = os.path.dirname(os.path.dirname(_file_))
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

def page_meta_bar(module_name: str, description: str) -> None:
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
