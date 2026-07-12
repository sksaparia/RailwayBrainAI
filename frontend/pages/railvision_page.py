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
from frontend.ui_helpers import recommendation_box, render_stat_grid, section_title, status_pill

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
    log_event("railvision", "INFO", f"Fatigue event recorded: {result.status} ({source_type})")
    return screenshot_path


def _tone_for_status(status: str) -> str:
    return {"SAFE": "safe", "WARNING": "warn", "DROWSY": "danger"}.get(status, "")


def _render_result(result) -> None:
    st.markdown(status_pill(result.status), unsafe_allow_html=True)
    st.caption(f"Detected at {result.detection_time}")

    tone = _tone_for_status(result.status)
    render_stat_grid([
        ("Risk Level", result.risk_level, tone),
        ("Fatigue Probability", f"{result.fatigue_probability * 100:.0f}%", tone),
        ("Confidence Score", f"{result.confidence_score}%", ""),
        ("Number of Faces", str(result.faces_detected), ""),
        ("Blink Count", str(result.blink_count), ""),
        ("Eye Closure %", f"{result.eye_closure_pct}%", tone),
        ("Driver Attention %", f"{result.attention_score}%", "safe" if result.attention_score >= 65 else ""),
        ("Fatigue Score", f"{result.fatigue_score}/100", tone),
    ])

    reco_level = "danger" if result.status == "DROWSY" else ("safe" if result.status == "SAFE" else "info")
    recommendation_box(result.recommendation, level=reco_level)

    if result.annotated_frame is not None:
        st.caption("Screenshot Preview")
        st.image(
            cv2.cvtColor(result.annotated_frame, cv2.COLOR_BGR2RGB),
            caption="Annotated detection (green = eyes, orange = face)",
            width="stretch",
        )


def render() -> None:
    section_title("RailVision AI \u2014 Driver Fatigue Detection")
    st.caption(
        "OpenCV Haar-cascade based fatigue pipeline. This is the software-only, "
        "laptop-buildable version of proposal IC0000000170 (full hardware spec uses "
        "dual 4K/IR cameras + NVIDIA Jetson + YOLOv9, described in the About page)."
    )

    engine = get_engine()
    tab_img, tab_vid, tab_history = st.tabs(["\U0001F5BC\uFE0F Image Upload", "\U0001F3A5 Video Upload", "\U0001F4CB Event History"])

    with tab_img:
        uploaded = st.file_uploader("Upload a driver-facing image (jpg/png)", type=["jpg", "jpeg", "png"], key="img_up")
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
                    st.success(f"Event saved. Screenshot: {path or 'not applicable'}")

    with tab_vid:
        uploaded_vid = st.file_uploader("Upload a short driver-facing video (mp4/avi)", type=["mp4", "avi", "mov"], key="vid_up")
        if uploaded_vid is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_vid.name)[1]) as tmp:
                tmp.write(uploaded_vid.read())
                tmp_path = tmp.name
            with st.spinner("Analysing video frames (sampled every 5th frame, max 150 frames)..."):
                result = engine.analyse_video(tmp_path)
            os.unlink(tmp_path)
            st.info(f"Frames analysed: {result.frames_analysed} | Faces detected across frames: {result.faces_detected}")
            _render_result(result)
            if st.button("Save this event to database", key="save_vid"):
                path = _save_event("video", uploaded_vid.name, result)
                st.success(f"Event saved. Screenshot: {path or 'not applicable'}")

        st.markdown(
            '<span class="rb-sim-badge">NOTE</span> Live webcam capture is disabled in this '
            "hosted demo environment (no camera device available server-side). In a real "
            "cab deployment, RailVision AI ingests a continuous camera stream instead of file uploads.",
            unsafe_allow_html=True,
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
            from backend.railvision.fatigue_engine import RISK_LEVEL_LABELS
            df = pd.DataFrame([dict(r) for r in rows])
            df["fatigue_probability"] = (df["fatigue_score"] / 100.0).round(2)
            df["risk_level"] = df["status"].map(RISK_LEVEL_LABELS).fillna("Unable to Assess")
            df = df.rename(columns={"created_at": "detection_time"})
            st.dataframe(df, width="stretch", hide_index=True)
