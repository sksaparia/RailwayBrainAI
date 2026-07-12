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
from backend.tracksentinel.ml_predictor import (
    predict_next_crack,
    model_info,
    fit_empirical_growth_rate,
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
                    gauge_chart(result.risk_score, "Risk Score", color="#ea580c"),
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
            fig.add_hline(y=critical, line_dash="dash", line_color="#dc2626",
                           annotation_text="Critical length")
            fig.update_traces(line_color="#ea580c", marker_color="#ea580c")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#1e293b", xaxis=dict(gridcolor="#dbe3ec"), yaxis=dict(gridcolor="#dbe3ec"),
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(history_df, width="stretch", hide_index=True)

            # ---- Physics vs ML comparison (trained RandomForest) --------
            section_title("Physics vs Machine Learning \u2014 Cross-Check")
            st.caption(
                "The physics model (Paris Law) says what SHOULD happen from material "
                "constants. The ML model (a RandomForest trained on multi-cycle histories) "
                "says what the DATA pattern suggests. When they agree, confidence is high; "
                "when they diverge, that track deserves a closer look."
            )

            # Empirical growth rate from the FULL history (run-on-run analysis)
            empirical_rate = fit_empirical_growth_rate(history_df)
            prev_rate = empirical_rate if empirical_rate is not None else None

            ml = predict_next_crack(
                float(latest["crack_length_mm"]), rail_grade,
                prev_growth_rate=prev_rate, mgt_step=10.0,
            )

            mcol1, mcol2 = st.columns([1, 1])
            with mcol1:
                bar = go.Figure()
                bar.add_trace(go.Bar(
                    name="Physics (Paris Law)", x=["Next crack (+10 MGT)"],
                    y=[ml.physics_next_crack_mm], marker_color="#2563eb",
                ))
                bar.add_trace(go.Bar(
                    name="ML (RandomForest)", x=["Next crack (+10 MGT)"],
                    y=[ml.predicted_next_crack_mm], marker_color="#ea580c",
                ))
                bar.update_layout(
                    barmode="group", height=280, title="Next-Reading Forecast",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#1e293b", legend=dict(orientation="h", y=1.2),
                    yaxis=dict(title="Crack length (mm)", gridcolor="#dbe3ec"),
                )
                st.plotly_chart(bar, width="stretch")
            with mcol2:
                agree_tone = ("safe" if ml.agreement_pct >= 80
                              else "warn" if ml.agreement_pct >= 50 else "danger")
                render_stat_grid([
                    ("Physics Forecast", f"{ml.physics_next_crack_mm} mm", ""),
                    ("ML Forecast", f"{ml.predicted_next_crack_mm} mm", "accent"),
                    ("Physics vs ML Agreement", f"{ml.agreement_pct}%", agree_tone),
                    ("Empirical Rate (full history)",
                     f"{empirical_rate} mm/MGT" if empirical_rate is not None else "n/a", ""),
                    ("ML Model Accuracy (MAE)", f"\u00b1{ml.model_mae_mm} mm", ""),
                    ("Model Trained On", f"{ml.training_samples:,} samples", ""),
                ])
            recommendation_box(
                ml.verdict,
                level="safe" if ml.agreement_pct >= 80 else
                      ("info" if ml.agreement_pct >= 50 else "danger"),
                label="ML Cross-Check Verdict",
            )
            st.markdown(
                '<span class="rb-sim-badge">REAL ML</span> RandomForestRegressor trained '
                "live on synthetic multi-cycle histories. In production this same model "
                "retrains on real RDSO USFD archives \u2014 the code path is identical.",
                unsafe_allow_html=True,
            )

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

                # Run-on-run enhancement: fit empirical growth rate from EACH
                # track's full history (uses every reading, not just the latest).
                df_in_dt = df_in.copy()
                df_in_dt["inspection_date"] = pd.to_datetime(
                    df_in_dt["inspection_date"], errors="coerce")
                empirical_rates = {}
                for tid, grp in df_in_dt.groupby("track_id"):
                    grp_sorted = grp.sort_values("inspection_date")
                    empirical_rates[tid] = fit_empirical_growth_rate(grp_sorted)
                results_df["empirical_rate_mm_per_mgt"] = results_df["track_id"].map(
                    empirical_rates)

                st.success(
                    f"Analysed {len(results_df)} track(s) using full run-on-run history "
                    f"(every reading, not just the latest)."
                )
                st.dataframe(results_df, width="stretch", hide_index=True)

                fig = px.bar(
                    results_df, x="track_id", y="risk_score", color="risk_band",
                    color_discrete_map={"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"},
                    title="Risk Score by Track",
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#1e293b", xaxis=dict(gridcolor="#dbe3ec"), yaxis=dict(gridcolor="#dbe3ec"),
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
            colorscale=[[0, "#16a34a"], [0.5, "#d97706"], [1, "#dc2626"]],
        ))
        fig_heat.update_layout(
            height=200, title="Track Risk Heatmap",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#1e293b",
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
