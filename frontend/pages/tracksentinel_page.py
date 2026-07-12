"""RailwayBrain AI - TrackSentinel AI page (rail defect growth prediction)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.database.db_manager import execute, fetch_all
from backend.tracksentinel.crack_growth_model import (
    RAIL_GRADE_CONSTANTS,
    _cost_of_delay_per_week,
    _inspection_grade,
    MAINTENANCE_PRIORITY,
    ASSUMED_MGT_PER_DAY,
    analyse_track,
    analyse_uploaded_csv,
    generate_synthetic_inspection_history,
)
from frontend.ui_helpers import gauge_chart, recommendation_box, render_stat_grid, section_title, status_pill


def _persist_result(result, rail_grade: str) -> None:
    execute(
        """INSERT INTO inspection_results
           (track_id, inspection_date, crack_length_mm, mgt_cumulative,
            crack_growth_rate, risk_score, remaining_life_mgt, recommendation, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (result.track_id, datetime.utcnow().strftime("%Y-%m-%d"), 0.0, 0.0,
         result.crack_growth_rate, result.risk_score, result.remaining_life_mgt,
         result.recommendation, datetime.utcnow().isoformat()),
    )


def render() -> None:
    section_title("TrackSentinel AI \u2014 Rail Defect Growth Prediction")
    st.caption(
        "Paris Law fatigue-crack model (da/dN = C\u00b7\u0394K\u1d50), calibrated per rail grade, "
        "applied to USFD run-on-run inspection data. Matches proposal IS0000000165."
    )

    tracks = fetch_all("SELECT track_id, rail_grade, zone, division FROM tracks ORDER BY track_id")
    track_ids = [t["track_id"] for t in tracks]
    track_grade = {t["track_id"]: t["rail_grade"] for t in tracks}

    tab_single, tab_csv, tab_dashboard = st.tabs(
        ["\U0001F50D Analyse Single Track", "\U0001F4C4 Upload USFD CSV", "\U0001F4CA Risk Dashboard"]
    )

    with tab_single:
        col1, col2 = st.columns(2)
        with col1:
            selected_track = st.selectbox("Track segment", track_ids) if track_ids else None
        with col2:
            rail_grade = st.selectbox(
                "Rail grade", list(RAIL_GRADE_CONSTANTS.keys()),
                index=list(RAIL_GRADE_CONSTANTS.keys()).index(track_grade.get(selected_track, "90UTS"))
                if selected_track else 0,
            )

        st.markdown(
            '<span class="rb-sim-badge">SIMULATED USFD HISTORY</span> '
            "Generates a synthetic multi-cycle inspection history for this track since "
            "no live USFD feed is connected in this demo.",
            unsafe_allow_html=True,
        )

        if selected_track and st.button("Generate & Analyse", type="primary"):
            history_df = generate_synthetic_inspection_history(selected_track, rail_grade, cycles=8)
            latest = history_df.iloc[-1]
            result = analyse_track(selected_track, float(latest["crack_length_mm"]), rail_grade,
                                    data_points=len(history_df))
            _persist_result(result, rail_grade)

            gcol, scol = st.columns([1, 2])
            with gcol:
                st.markdown('<div class="rb-gauge-wrap">', unsafe_allow_html=True)
                st.plotly_chart(
                    gauge_chart(result.risk_score, "Risk Score", color="#ff7a1a"),
                    width="stretch",
                )
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(status_pill(result.risk_band), unsafe_allow_html=True)
                st.markdown(f"**Inspection Grade:** {result.inspection_grade}")
            with scol:
                render_stat_grid([
                    ("Maintenance Priority", result.maintenance_priority, ""),
                    ("Critical Crack Length", f"{result.critical_crack_length_mm} mm", ""),
                    ("Crack Growth Rate", f"{result.crack_growth_rate} mm/MGT", ""),
                    ("Remaining Life", f"{result.remaining_life_mgt} MGT", ""),
                    ("Estimated Remaining Days", f"{result.estimated_remaining_days:,.0f} days", ""),
                    ("Confidence Score", f"{result.confidence_score}%", ""),
                    ("Cost of Delay (per week)", f"\u20b9{result.cost_of_delay_per_week_inr:,.0f}*", ""),
                ])
                st.caption(
                    "*Illustrative cost estimate (speed restriction + inspection overtime + "
                    "capacity loss) \u2014 not a Railway-sourced figure."
                )

            recommendation_box(result.recommendation,
                                level="danger" if result.risk_band == "HIGH" else
                                      ("safe" if result.risk_band == "LOW" else "info"))
            with st.expander("Engineering Notes"):
                st.write(result.engineering_notes)

            fig = px.line(
                history_df, x="mgt_cumulative", y="crack_length_mm", markers=True,
                title=f"Crack Growth Curve — {selected_track} ({rail_grade})",
                labels={"mgt_cumulative": "Cumulative MGT", "crack_length_mm": "Crack length (mm)"},
            )
            critical = RAIL_GRADE_CONSTANTS[rail_grade]["critical_length_mm"]
            fig.add_hline(y=critical, line_dash="dash", line_color="#ff4d4f",
                           annotation_text="Critical length")
            fig.update_traces(line_color="#ff7a1a", marker_color="#ff7a1a")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e7ecf5", xaxis=dict(gridcolor="#22304f"), yaxis=dict(gridcolor="#22304f"),
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(history_df, width="stretch", hide_index=True)

    with tab_csv:
        st.write("CSV columns required: `track_id, inspection_date, crack_length_mm, mgt_cumulative`")
        csv_grade = st.selectbox("Rail grade to apply (if not per-row)", list(RAIL_GRADE_CONSTANTS.keys()), key="csv_grade")
        uploaded = st.file_uploader("Upload USFD inspection CSV", type=["csv"])

        if st.button("Generate sample CSV template"):
            sample = generate_synthetic_inspection_history("ECR-DHN-101", csv_grade, cycles=6)
            st.download_button(
                "Download sample_inspection_data.csv",
                sample.to_csv(index=False).encode("utf-8"),
                file_name="sample_inspection_data.csv",
                mime="text/csv",
            )
            st.dataframe(sample, width="stretch", hide_index=True)

        if uploaded is not None:
            try:
                df_in = pd.read_csv(uploaded)
                results_df = analyse_uploaded_csv(df_in, rail_grade=csv_grade)
                st.success(f"Analysed {len(results_df)} track(s).")
                st.dataframe(results_df, width="stretch", hide_index=True)

                fig = px.bar(
                    results_df, x="track_id", y="risk_score", color="risk_band",
                    color_discrete_map={"HIGH": "#ff4d4f", "MEDIUM": "#f5b942", "LOW": "#2ecc71"},
                    title="Risk Score by Track",
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e7ecf5", xaxis=dict(gridcolor="#22304f"), yaxis=dict(gridcolor="#22304f"),
                )
                st.plotly_chart(fig, width="stretch")
            except ValueError as exc:
                st.error(str(exc))

    with tab_dashboard:
        rows = fetch_all(
            "SELECT track_id, risk_score, crack_growth_rate, remaining_life_mgt, "
            "recommendation, created_at FROM inspection_results ORDER BY created_at DESC LIMIT 200"
        )
        if not rows:
            st.info("No inspection results yet. Run an analysis in the other tabs first.")
            return

        df = pd.DataFrame([dict(r) for r in rows])
        latest_per_track = df.sort_values("created_at").groupby("track_id").tail(1)

        high = (latest_per_track["risk_score"] >= 70).sum()
        med = ((latest_per_track["risk_score"] >= 40) & (latest_per_track["risk_score"] < 70)).sum()
        low = (latest_per_track["risk_score"] < 40).sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("High Risk Tracks", int(high))
        c2.metric("Medium Risk Tracks", int(med))
        c3.metric("Low Risk Tracks", int(low))

        fig_heat = go.Figure(data=go.Heatmap(
            z=[latest_per_track["risk_score"].tolist()],
            x=latest_per_track["track_id"].tolist(),
            colorscale=[[0, "#2ecc71"], [0.5, "#f5b942"], [1, "#ff4d4f"]],
        ))
        fig_heat.update_layout(
            height=200, title="Track Risk Heatmap",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e7ecf5",
        )
        st.plotly_chart(fig_heat, width="stretch")

        priority = latest_per_track.sort_values("risk_score", ascending=False).copy()
        priority["inspection_grade"] = priority["risk_score"].apply(_inspection_grade)
        priority["maintenance_priority"] = priority.apply(
            lambda r: MAINTENANCE_PRIORITY.get(
                "HIGH" if r["risk_score"] >= 70 else ("MEDIUM" if r["risk_score"] >= 40 else "LOW"),
                "P3 \u2014 Routine",
            ), axis=1,
        )
        priority["estimated_remaining_days"] = (priority["remaining_life_mgt"] / ASSUMED_MGT_PER_DAY).round(0)
        st.markdown("**Priority ranking (highest risk first):**")
        st.dataframe(priority, width="stretch", hide_index=True)
