"""
RailwayBrain AI - Main Application Entrypoint
--------------------------------------------------
Run with:  streamlit run app.py

This is ONE unified Streamlit application (not three separate demos).
Navigation between Dashboard / RailVision AI / TrackSentinel AI /
SmartSeal AI / Reports / Settings / About happens through the sidebar,
all sharing one SQLite database and one enterprise dark theme.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import streamlit as st

# Make the project root importable regardless of the working directory
# Streamlit is launched from.
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database.db_manager import init_db  # noqa: E402
from backend.database.seed_data import seed_all  # noqa: E402
from frontend.ui_helpers import brand_header, footer, load_css, load_logo_svg, page_meta_bar  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("railwaybrain.app")

st.set_page_config(
    page_title="RailwayBrain AI",
    page_icon="\U0001F9E0",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODULES = {
    "Dashboard": "\U0001F4CA",
    "RailVision AI": "\U0001F441\uFE0F",
    "TrackSentinel AI": "\U0001F6E4\uFE0F",
    "SmartSeal AI": "\U0001F512",
    "Reports": "\U0001F4C4",
    "Settings": "\u2699\uFE0F",
    "About": "\u2139\uFE0F",
}

MODULE_DESCRIPTIONS = {
    "Dashboard": "Real-time operations overview across all RailwayBrain AI modules.",
    "RailVision AI": "Camera-based driver fatigue and drowsiness detection.",
    "TrackSentinel AI": "Physics-based rail defect growth prediction and maintenance planning.",
    "SmartSeal AI": "Freight consignment security simulation with tamper detection and RPF alerts.",
    "Reports": "Export module data as CSV/PDF and view cross-module analytics.",
    "Settings": "Database management and demo data controls.",
    "About": "Project background, real-vs-simulated capabilities, and roadmap.",
}


def _bootstrap() -> None:
    """Initialise DB schema + seed demo data exactly once per session."""
    if "rb_bootstrapped" not in st.session_state:
        with st.spinner("Booting RailwayBrain AI engine..."):
            init_db()
            seed_all()
            time.sleep(0.4)  # brief, deliberate splash pause
        st.session_state["rb_bootstrapped"] = True
        logger.info("RailwayBrain AI bootstrapped successfully.")


def _sidebar_nav() -> str:
    with st.sidebar:
        logo_svg = load_logo_svg()
        st.markdown(
            f'<div style="text-align:center; padding: 6px 0 14px 0;">'
            f'<div style="width:96px;height:96px;margin:0 auto;" class="rb-logo-wrap">{logo_svg}</div>'
            f'<div class="rb-brand-title" style="margin-top:8px;">RAILWAYBRAIN'
            f'<span class="accent"> AI</span></div>'
            f'<div class="rb-brand-sub">Indian Railways \u2022 AI Platform</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        selection = st.radio(
            "Navigate",
            list(MODULES.keys()),
            format_func=lambda m: f"{MODULES[m]}  {m}",
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("Vande Bharatam Innovation Challenge \u2014 Adani Group")
        st.caption("Founder: Sachin Saparia \u2022 Jamshedpur, Jharkhand")
        st.markdown(
            '<span class="rb-sim-badge">DEMO BUILD</span> Zero-cost software MVP',
            unsafe_allow_html=True,
        )
    return selection


def main() -> None:
    load_css()
    _bootstrap()

    page = _sidebar_nav()
    brand_header()
    page_meta_bar(page, MODULE_DESCRIPTIONS.get(page, ""))

    if page == "Dashboard":
        from frontend.pages import dashboard_page
        dashboard_page.render()
    elif page == "RailVision AI":
        from frontend.pages import railvision_page
        railvision_page.render()
    elif page == "TrackSentinel AI":
        from frontend.pages import tracksentinel_page
        tracksentinel_page.render()
    elif page == "SmartSeal AI":
        from frontend.pages import smartseal_page
        smartseal_page.render()
    elif page == "Reports":
        from frontend.pages import reports_page
        reports_page.render()
    elif page == "Settings":
        from frontend.pages import settings_page
        settings_page.render()
    elif page == "About":
        from frontend.pages import about_page
        about_page.render()

    footer()


if __name__ == "__main__":
    main()
