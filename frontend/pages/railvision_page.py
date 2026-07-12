"""RailwayBrain AI - RailVision AI page (driver fatigue detection)."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

import cv2
import numpy as np
import streamlit as st

from backend.database.db_manager import execute, fetch_all, log_event
from backend.railvision.fatigue_engine import FatigueEngine, save_screenshot
from frontend.ui_helpers import render_stat_grid, section_title, status_pill

SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "screenshots", "railvision"
)


@st.cache_resource
def get_engine() -> FatigueEngine:
    return FatigueEngine()


def _save_event(source_type: str, source_name: str, result, driver_id=None) -> str:
    screenshot_path = ""
    if result.annotated_frame is not None:
        screenshot_path = save_screenshot(result.annotated_frame, SCREENSHOT_DIR)
    execute(
        """INSERT INTO fatigue_events
           (driver_id, source_type, source_name, status, fatigue_score, attention_score,
            blink_count, eye_closure_pct, screenshot_path, recommendation, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (driver_id, source_type, source_name, result.status, result.fatigue_score,
         result.attention_score, result.blink_count, result.eye_closure_pct,
         screenshot_path, result.recommendation, datetime.utcnow().isoformat()),
    )
    log_event("railvision", "INFO", "Fatigue event recorded: " + result.status)
    return screenshot_path


def _show_recommendation(text: str, status: str) -> None:
    if status == "DROWSY":
        st.error("**AI Recommendation:** " + text)
    elif status == "WARNING":
        st.warning("**AI Recommendation:** " + text)
    elif status == "SAFE":
        st.success("**AI Recommendation:** " + text)
    else:
        st.info("**AI Recommendation:** " + text)


def _render_result(result) -> None:
    st.markdown(status_pill(result.status), unsafe_allow_html=True)
    st.caption("Detected at: " + result.detection_time)

    render_stat_grid([
        ("Risk Level", result.risk_level, ""),
        ("Fatigue Probability", str(round(result.fatigue_probability * 100, 0)) + "%", ""),
        ("Confidence Score", str(result.confidence_score) + "%", ""),
        ("Faces Detected", str(result.faces_detected), ""),
        ("Blink Count", str(result.blink_count), ""),
        ("Eye Closure %", str(result.eye_closure_pct) + "%", ""),
        ("Driver Attention %", str(result.attention_score) + "%", ""),
        ("Fatigue Score", str(result.fatigue_score) + "/100", ""),
    ])

    _show_recommendation(result.recommendation, result.status)

    if result.annotated_frame is not None:
        st.caption("Screenshot Preview")
        st.image(
            cv2.cvtColor(result.annotated_frame, cv2.COLOR_BGR2RGB),
            caption="Annotated detection (green = eyes, orange = face)",
        )


def render() -> None:
    section_title("RailVision AI — Driver Fatigue Detection")
    st.caption(
        "OpenCV Haar-cascade based fatigue pipeline. Software-only version of proposal IC0000000170."
    )

    engine = get_engine()
    tab_img, tab_vid, tab_history = st.tabs(["Image Upload", "Video Upload", "Event History"])

    with tab_img:
        uploaded = st.file_uploader(
            "Upload a driver-facing image (jpg/png)",
            type=["jpg", "jpeg", "png"],
            key="img_up"
        )
        if uploaded is not None:
            file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is None:
                st.error("Could not decode this image.")
            else:
                with st.spinner("Running fatigue detection..."):
                    result = engine.analyse_image(frame)
                _render_result(result)
                if st.button("Save this event to database", key="save_img"):
                    path = _save_event("image", uploaded.name, result)
                    st.success("Event saved.")

    with tab_vid:
        uploaded_vid = st.file_uploader(
            "Upload a short driver-facing video (mp4/avi)",
            type=["mp4", "avi", "mov"],
            key="vid_up"
        )
        if uploaded_vid is not None:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(uploaded_vid.name)[1]
            ) as tmp:
                tmp.write(uploaded_vid.read())
                tmp_path = tmp.name
            with st.spinner("Analysing video frames..."):
                result = engine.analyse_video(tmp_path)
            os.unlink(tmp_path)
            st.info("Frames analysed: " + str(result.frames_analysed))
            _render_result(result)
            if st.button("Save this event to database", key="save_vid"):
                _save_event("video", uploaded_vid.name, result)
                st.success("Event saved.")

        st.caption(
            "Live webcam is disabled in hosted demo. "
            "In real cab deployment, RailVision ingests a continuous camera stream."
        )

    with tab_history:
        rows = fetch_all(
            "SELECT event_id, source_type, source_name, status, fatigue_score, "
            "attention_score, blink_count, eye_closure_pct, created_at "
            "FROM fatigue_events ORDER BY created_at DESC LIMIT 100"
        )
        if not rows:
            st.info("No events recorded yet.")
        else:
            import pandas as pd
            df = pd.DataFrame([dict(r) for r in rows])
            df["fatigue_probability"] = (df["fatigue_score"] / 100.0).round(2)
            st.dataframe(df, hide_index=True)
