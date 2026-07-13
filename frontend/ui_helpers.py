"""
RailwayBrain AI - Shared UI Helpers
All components use 100% inline styles — no CSS class dependency.
This guarantees correct rendering on any Streamlit Cloud environment.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import streamlit as st

CSS_PATH = Path(__file__).parent / "css" / "theme.css"
FOUNDER_NAME = "Sachin Saparia"
FOOTER_ORG   = "Vande Bharatam Innovation Challenge — Adani Group"

# ── Brand colours (inline, no CSS dependency) ─────────────
NAVY   = "#0d3b66"
ORANGE = "#ea580c"
BLUE   = "#2563eb"
TEXT   = "#1e293b"
MUTED  = "#64748b"
BORDER = "#dbe3ec"
BG     = "#f8fafc"
WHITE  = "#ffffff"
SAFE   = "#16a34a"
WARN   = "#d97706"
DANGER = "#dc2626"


def load_css() -> None:
    """Load the CSS theme file (enhances appearance but not required for correctness)."""
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text()}</style>", unsafe_allow_html=True)


def load_logo_svg() -> str:
    logo = Path(__file__).parent.parent / "assets" / "logos" / "railwaybrain_logo.svg"
    if logo.exists():
        return logo.read_text()
    return ""


# ── KPI card (large, hero metric) ─────────────────────────
def kpi_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div style="font-size:0.75rem;color:{MUTED};margin-top:4px;">{sub}</div>' if sub else ""
    return (
        f'<div style="background:{WHITE};border:1px solid {BORDER};border-radius:12px;'
        f'padding:16px 20px;box-shadow:0 1px 3px rgba(13,59,102,0.08);">'
        f'<div style="font-size:0.76rem;color:{MUTED};text-transform:uppercase;'
        f'letter-spacing:0.07em;font-weight:600;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:1.9rem;font-weight:800;color:{NAVY};">{value}</div>'
        f'{sub_html}</div>'
    )


def render_kpi_row(cards: list) -> None:
    """Render a row of KPI cards. cards = [(label, value, sub), ...] or [(label, value, sub, accent), ...]"""
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        label, value = card[0], card[1]
        sub    = card[2] if len(card) > 2 else ""
        accent = card[3] if len(card) > 3 else False
        val_color = ORANGE if accent else NAVY
        sub_html = (f'<div style="font-size:0.75rem;color:{MUTED};margin-top:4px;">{sub}</div>'
                    if sub else "")
        col.markdown(
            f'<div style="background:{WHITE};border:1px solid {BORDER};border-radius:12px;'
            f'padding:16px 20px;box-shadow:0 1px 3px rgba(13,59,102,0.08);">'
            f'<div style="font-size:0.76rem;color:{MUTED};text-transform:uppercase;'
            f'letter-spacing:0.07em;font-weight:600;margin-bottom:6px;">{label}</div>'
            f'<div style="font-size:1.9rem;font-weight:800;color:{val_color};">{value}</div>'
            f'{sub_html}</div>',
            unsafe_allow_html=True,
        )


# ── Stat tile (small, grid metric) ────────────────────────
def stat_tile(label: str, value: str, tone: str = "") -> str:
    color = {"accent": ORANGE, "safe": SAFE, "warn": WARN, "danger": DANGER}.get(tone, NAVY)
    return (
        f'<div style="background:{WHITE};border:1px solid {BORDER};border-radius:10px;'
        f'padding:10px 14px;">'
        f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:3px;">{label}</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:{color};">{value}</div>'
        f'</div>'
    )


def render_stat_grid(items: list[tuple[str, str, str]]) -> None:
    """items = [(label, value, tone), ...]  tone: '' | 'accent' | 'safe' | 'warn' | 'danger'"""
    tiles = "".join(stat_tile(l, v, t) for l, v, t in items)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));'
        f'gap:10px;margin:10px 0;">{tiles}</div>',
        unsafe_allow_html=True,
    )


# ── Status pill ────────────────────────────────────────────
def status_pill(status: str, tone: str = "info") -> str:
    bg_map = {
        "safe":   (f"rgba(22,163,74,0.12)",  SAFE),
        "warn":   (f"rgba(217,119,6,0.12)",  WARN),
        "danger": (f"rgba(220,38,38,0.12)",  DANGER),
        "high":   (f"rgba(220,38,38,0.12)",  DANGER),
        "medium": (f"rgba(217,119,6,0.12)",  WARN),
        "low":    (f"rgba(22,163,74,0.12)",  SAFE),
        "info":   (f"rgba(37,99,235,0.12)",  BLUE),
    }
    bg, fg = bg_map.get(tone.lower(), bg_map["info"])
    return (
        f'<span style="display:inline-block;padding:4px 13px;border-radius:999px;'
        f'font-size:0.74rem;font-weight:700;letter-spacing:0.03em;'
        f'background:{bg};color:{fg};border:1px solid {fg}40;">{status}</span>'
    )


# ── Sim badge ──────────────────────────────────────────────
def sim_badge(text: str = "SIMULATED DATA") -> None:
    st.markdown(
        f'<span style="display:inline-block;background:rgba(234,88,12,0.10);'
        f'color:{ORANGE};border:1px dashed {ORANGE};border-radius:8px;'
        f'padding:2px 10px;font-size:0.72rem;font-weight:700;">⚡ {text}</span>',
        unsafe_allow_html=True,
    )


# ── Section title ──────────────────────────────────────────
def section_title(text: str, badge: str = "", simulated: bool = False) -> None:
    sim_html = ""
    if simulated:
        sim_html = (f'&nbsp;<span style="display:inline-block;background:rgba(234,88,12,0.10);'
                    f'color:{ORANGE};border:1px dashed {ORANGE};border-radius:8px;'
                    f'padding:1px 8px;font-size:0.7rem;font-weight:700;">⚡ SIMULATED DATA</span>')
    st.markdown(
        f'<div style="font-size:1.08rem;font-weight:700;color:{NAVY};'
        f'border-left:4px solid {ORANGE};padding-left:10px;margin:6px 0 14px 0;">'
        f'{text} {badge}{sim_html}</div>',
        unsafe_allow_html=True,
    )


# ── Brand header (used inside sidebar) ────────────────────
def brand_header(subtitle: str = "Unified AI Platform for Indian Railways") -> None:
    logo_svg = load_logo_svg()
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">'
        f'<div style="width:52px;height:52px;">{logo_svg}</div>'
        f'<div>'
        f'<div style="font-weight:800;font-size:1.4rem;color:#ffffff;letter-spacing:0.02em;">'
        f'RAILWAYBRAIN<span style="color:#ffb27a;"> AI</span></div>'
        f'<div style="color:#a8c2dd;font-size:0.78rem;">{subtitle}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ── Page meta bar ──────────────────────────────────────────
def page_meta_bar(module_name: str, description: str = "") -> None:
    clean = module_name.split("\u2003")[-1].strip() if "\u2003" in module_name else module_name.strip()
    emojis = {"Dashboard":"📊","RailVision AI":"👁️","TrackSentinel AI":"🛤️",
               "SmartSeal AI":"🔒","Reports":"📄","Settings":"⚙️","About":"ℹ️"}
    for k, v in emojis.items():
        if k in clean:
            clean = clean.replace(k, "").strip()
            break
    now = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:8px;padding:10px 16px;margin:4px 0 16px 0;'
        f'background:linear-gradient(90deg,#eef4fa,#f8fafc);'
        f'border:1px solid {BORDER};border-left:4px solid {NAVY};border-radius:10px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">'
        f'<span style="font-size:0.88rem;font-weight:800;color:{NAVY};">{clean}</span>'
        f'<span style="font-size:0.78rem;color:{MUTED};">{description}</span>'
        f'</div>'
        f'<div style="font-size:0.75rem;color:{MUTED};">🕑 {now}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Recommendation box ─────────────────────────────────────
def recommendation_box(text: str, level: str = "info", label: str = "AI Recommendation") -> None:
    icon  = {"safe": "✅", "danger": "⚠️", "info": "💡"}.get(level, "💡")
    color = {"safe": SAFE, "danger": DANGER, "info": ORANGE}.get(level, ORANGE)
    bg    = {"safe": "rgba(22,163,74,0.07)", "danger": "rgba(220,38,38,0.07)",
             "info": "rgba(234,88,12,0.10)"}.get(level, "rgba(234,88,12,0.10)")
    st.markdown(
        f'<div style="display:flex;gap:12px;align-items:flex-start;background:{bg};'
        f'border:1px solid {color}40;border-left:4px solid {color};'
        f'border-radius:10px;padding:14px 16px;margin:10px 0;">'
        f'<div style="font-size:1.3rem;">{icon}</div>'
        f'<div><div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;'
        f'color:{MUTED};margin-bottom:3px;">{label}</div>'
        f'<div style="font-size:0.9rem;color:{TEXT};line-height:1.45;">{text}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ── Mini timeline ──────────────────────────────────────────
def mini_timeline(events: list[tuple[str, str, str]]) -> None:
    """events = [(timestamp_str, module_name, message), ...]"""
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:10px;padding:7px 4px;'
        f'border-bottom:1px solid {BORDER};font-size:0.82rem;">'
        f'<span style="color:{MUTED};font-size:0.72rem;min-width:118px;">{t}</span>'
        f'<span style="color:{BLUE};font-weight:700;min-width:100px;font-size:0.75rem;">{m}</span>'
        f'<span style="color:{TEXT};">{txt}</span></div>'
        for t, m, txt in events
    )
    st.markdown(
        f'<div style="display:flex;flex-direction:column;gap:2px;">{rows}</div>',
        unsafe_allow_html=True,
    )


# ── Gauge chart (plotly) ───────────────────────────────────
def gauge_chart(value: float, title: str, color: str | None = None) -> "go.Figure":
    import plotly.graph_objects as go
    c = color or (DANGER if value >= 70 else WARN if value >= 40 else SAFE)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": NAVY, "size": 13}},
        number={"font": {"color": c, "size": 32}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED},
            "bar": {"color": c},
            "bgcolor": BG,
            "borderwidth": 1, "bordercolor": BORDER,
            "steps": [
                {"range": [0,  40], "color": "rgba(22,163,74,0.12)"},
                {"range": [40, 70], "color": "rgba(217,119,6,0.12)"},
                {"range": [70,100], "color": "rgba(220,38,38,0.12)"},
            ],
        },
    ))
    fig.update_layout(
        height=230, margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font_color=NAVY,
    )
    return fig


# ── Footer ─────────────────────────────────────────────────
def footer() -> None:
    st.markdown(
        f'<div style="margin-top:32px;padding-top:14px;border-top:1px solid {BORDER};'
        f'display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;">'
        f'<div style="font-size:0.72rem;color:{MUTED};">'
        f'<b style="color:{NAVY};">RailwayBrain AI</b> &nbsp;•&nbsp; {FOOTER_ORG}</div>'
        f'<div style="font-size:0.72rem;color:{MUTED};">'
        f'Founder: <b style="color:{NAVY};">{FOUNDER_NAME}</b> &nbsp;•&nbsp; © 2026</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
