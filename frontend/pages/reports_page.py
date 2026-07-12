"""RailwayBrain AI - Reports page (PDF/CSV export, analytics)."""

from __future__ import annotations

import io
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.database.db_manager import fetch_all
from frontend.ui_helpers import FOUNDER_NAME, section_title

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logos", "railwaybrain_logo.svg"
)

TABLE_OPTIONS = {
    "Fatigue Events (RailVision AI)": (
        "fatigue_events",
        "SELECT event_id, source_type, source_name, status, fatigue_score, "
        "attention_score, blink_count, eye_closure_pct, recommendation, created_at "
        "FROM fatigue_events ORDER BY created_at DESC",
    ),
    "Inspection Results (TrackSentinel AI)": (
        "inspection_results",
        "SELECT result_id, track_id, crack_growth_rate, risk_score, remaining_life_mgt, "
        "recommendation, created_at FROM inspection_results ORDER BY created_at DESC",
    ),
    "Tamper Events (SmartSeal AI)": (
        "tamper_events",
        "SELECT event_id, wagon_id, tamper_type, severity, resolved, "
        "rpf_recommendation, created_at FROM tamper_events ORDER BY created_at DESC",
    ),
    "System Logs": (
        "system_logs",
        "SELECT log_id, module, level, message, created_at FROM system_logs ORDER BY created_at DESC",
    ),
}


def _dataset_kind(df: pd.DataFrame) -> str:
    cols = set(df.columns)
    if "fatigue_score" in cols:
        return "fatigue"
    if "risk_score" in cols:
        return "inspection"
    if "tamper_type" in cols:
        return "tamper"
    if "level" in cols and "module" in cols:
        return "logs"
    return "generic"


def _stats_and_distribution(kind: str, df: pd.DataFrame) -> tuple[list[tuple[str, str]], dict]:
    """Returns (stats list of (label, value), distribution dict for the chart)."""
    if df.empty:
        return [("Total Records", "0")], {}

    if kind == "fatigue":
        dist = df["status"].value_counts().to_dict()
        stats = [
            ("Total Events", str(len(df))),
            ("Average Fatigue Score", f"{df['fatigue_score'].mean():.1f}/100"),
            ("Average Attention Score", f"{df['attention_score'].mean():.1f}/100"),
            ("Drowsy Events", str(dist.get("DROWSY", 0))),
        ]
        return stats, dist

    if kind == "inspection":
        band = df["risk_score"].apply(lambda s: "HIGH" if s >= 70 else ("MEDIUM" if s >= 40 else "LOW"))
        dist = band.value_counts().to_dict()
        stats = [
            ("Total Inspections", str(len(df))),
            ("Average Risk Score", f"{df['risk_score'].mean():.1f}/100"),
            ("High Risk Tracks", str(dist.get("HIGH", 0))),
            ("Average Remaining Life", f"{df['remaining_life_mgt'].mean():.1f} MGT"),
        ]
        return stats, dist

    if kind == "tamper":
        dist = df["severity"].value_counts().to_dict()
        stats = [
            ("Total Tamper Events", str(len(df))),
            ("Unresolved", str(int((df["resolved"] == 0).sum()))),
            ("High Severity", str(dist.get("HIGH", 0))),
            ("Resolved", str(int((df["resolved"] == 1).sum()))),
        ]
        return stats, dist

    if kind == "logs":
        dist = df["level"].value_counts().to_dict()
        stats = [
            ("Total Log Entries", str(len(df))),
            ("Errors", str(dist.get("ERROR", 0))),
            ("Warnings", str(dist.get("WARNING", 0))),
            ("Info", str(dist.get("INFO", 0))),
        ]
        return stats, dist

    return [("Total Records", str(len(df)))], {}


def _top_recommendations(kind: str, df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    if kind == "fatigue" and "recommendation" in df.columns:
        subset = df[df["status"] == "DROWSY"]["recommendation"].dropna().unique().tolist()
        return subset[:3] or df["recommendation"].dropna().unique().tolist()[:3]
    if kind == "inspection" and "recommendation" in df.columns:
        subset = df[df["risk_score"] >= 70]["recommendation"].dropna().unique().tolist()
        return subset[:3] or df["recommendation"].dropna().unique().tolist()[:3]
    if kind == "tamper" and "rpf_recommendation" in df.columns:
        subset = df[(df["resolved"] == 0) & (df["severity"] == "HIGH")]["rpf_recommendation"].dropna().unique().tolist()
        return subset[:3] or df["rpf_recommendation"].dropna().unique().tolist()[:3]
    return []


def _summary_text(kind: str, choice: str, df: pd.DataFrame) -> str:
    if df.empty:
        return f"No records are currently available for {choice}."
    if kind == "fatigue":
        drowsy = int((df["status"] == "DROWSY").sum())
        return (
            f"This report covers {len(df)} driver monitoring event(s) captured by RailVision AI. "
            f"{drowsy} event(s) were classified DROWSY and require follow-up. Average fatigue "
            f"score across all events is {df['fatigue_score'].mean():.1f} out of 100."
        )
    if kind == "inspection":
        high = int((df["risk_score"] >= 70).sum())
        return (
            f"This report covers {len(df)} track inspection result(s) from TrackSentinel AI's "
            f"Paris Law crack-growth model. {high} section(s) are currently at HIGH risk and "
            f"should be prioritised for maintenance."
        )
    if kind == "tamper":
        open_events = int((df["resolved"] == 0).sum())
        return (
            f"This report covers {len(df)} freight seal tamper event(s) from SmartSeal AI. "
            f"{open_events} event(s) remain unresolved and are pending RPF verification."
        )
    if kind == "logs":
        errors = int((df["level"] == "ERROR").sum())
        return f"This report covers {len(df)} system log entries, including {errors} error(s)."
    return f"This report covers {len(df)} record(s) for {choice}."


def _bar_chart_drawing(distribution: dict, color_map: dict) -> Drawing:
    """Small embedded bar chart of a category distribution (status/severity/risk band)."""
    d = Drawing(420, 160)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 20
    chart.width = 350
    chart.height = 120
    categories = list(distribution.keys())
    values = list(distribution.values())
    chart.data = [values]
    chart.categoryAxis.categoryNames = categories
    chart.valueAxis.valueMin = 0
    chart.bars[0].fillColor = colors.HexColor("#ff7a1a")
    for i, cat in enumerate(categories):
        hex_color = color_map.get(cat)
        if hex_color:
            chart.bars[(0, i)].fillColor = colors.HexColor(hex_color)
    d.add(chart)
    return d


DIST_COLOR_MAPS = {
    "fatigue": {"SAFE": "#2ecc71", "WARNING": "#f5b942", "DROWSY": "#ff4d4f", "UNKNOWN": "#3fa9f5"},
    "inspection": {"HIGH": "#ff4d4f", "MEDIUM": "#f5b942", "LOW": "#2ecc71"},
    "tamper": {"HIGH": "#ff4d4f", "MEDIUM": "#f5b942", "LOW": "#2ecc71"},
    "logs": {"ERROR": "#ff4d4f", "WARNING": "#f5b942", "INFO": "#3fa9f5"},
}


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    left_text = f"RailwayBrain AI \u2022 Founder: {FOUNDER_NAME}"
    right_text = f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')} \u2022 Page {doc.page}"
    canvas.drawString(18 * mm, 11 * mm, left_text)
    canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, right_text)
    canvas.restoreState()


def _build_pdf_report(title: str, df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=24 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("RBTitle", parent=styles["Title"], textColor=colors.HexColor("#16223f"))
    heading_style = ParagraphStyle("RBHeading", parent=styles["Heading2"], textColor=colors.HexColor("#16223f"),
                                    spaceBefore=10, spaceAfter=6)
    meta_style = ParagraphStyle("RBMeta", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    body_style = ParagraphStyle("RBBody", parent=styles["Normal"], fontSize=9.5, leading=13)

    kind = _dataset_kind(df)
    elements = []

    # --- Header: logo + title ---
    try:
        from svglib.svglib import svg2rlg
        logo_drawing = svg2rlg(LOGO_PATH)
        scale = 32.0 / logo_drawing.height
        logo_drawing.width *= scale
        logo_drawing.height *= scale
        logo_drawing.scale(scale, scale)
        header_table = Table(
            [[logo_drawing, Paragraph("RailwayBrain AI", title_style)]],
            colWidths=[40, None],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
    except Exception:
        elements.append(Paragraph("RailwayBrain AI", title_style))

    elements.append(Paragraph("Vande Bharatam Innovation Challenge \u2014 Adani Group", meta_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(title, styles["Heading2"]))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')} &nbsp;|&nbsp; Founder: {FOUNDER_NAME} "
        f"&nbsp;|&nbsp; Rows: {len(df)}", meta_style,
    ))
    elements.append(Spacer(1, 10))

    # --- Summary ---
    elements.append(Paragraph("Summary", heading_style))
    elements.append(Paragraph(_summary_text(kind, title, df), body_style))

    # --- Statistics ---
    stats, distribution = _stats_and_distribution(kind, df)
    elements.append(Paragraph("Statistics", heading_style))
    stat_table = Table([[label, value] for label, value in stats], colWidths=[220, 200])
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f4f8")),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(stat_table)

    # --- Graph ---
    if distribution:
        elements.append(Paragraph("Distribution", heading_style))
        elements.append(_bar_chart_drawing(distribution, DIST_COLOR_MAPS.get(kind, {})))

    # --- Recommendations ---
    recos = _top_recommendations(kind, df)
    elements.append(Paragraph("Recommendations", heading_style))
    if recos:
        for r in recos:
            elements.append(Paragraph(f"\u2022 {r}", body_style))
            elements.append(Spacer(1, 3))
    else:
        elements.append(Paragraph("No urgent recommendations \u2014 all records within normal range.", body_style))

    # --- Data table ---
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Detailed Records", heading_style))
    if df.empty:
        elements.append(Paragraph("No data available for this report.", body_style))
    else:
        display_df = df.copy()
        for col in display_df.columns:
            display_df[col] = display_df[col].astype(str).str.slice(0, 60)
        data = [list(display_df.columns)] + display_df.values.tolist()
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16223f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f8")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def render() -> None:
    section_title("Reports \u2014 Export & Analytics")

    choice = st.selectbox("Select dataset", list(TABLE_OPTIONS.keys()))
    _, query = TABLE_OPTIONS[choice]
    rows = fetch_all(query)
    df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()

    st.dataframe(df, width="stretch", hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "\U0001F4E5 Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"{choice.split(' ')[0].lower()}_report.csv",
            mime="text/csv",
            disabled=df.empty,
        )
    with col2:
        if st.button("\U0001F4C4 Generate PDF Report", disabled=df.empty):
            pdf_bytes = _build_pdf_report(choice, df)
            st.download_button(
                "\U0001F4E5 Download PDF",
                pdf_bytes,
                file_name=f"{choice.split(' ')[0].lower()}_report.pdf",
                mime="application/pdf",
            )

    st.markdown("<br/>", unsafe_allow_html=True)
    section_title("Cross-Module Analytics")

    fatigue_rows = fetch_all("SELECT status, COUNT(*) c FROM fatigue_events GROUP BY status")
    tamper_rows = fetch_all("SELECT severity, COUNT(*) c FROM tamper_events GROUP BY severity")
    risk_rows = fetch_all(
        "SELECT CASE WHEN risk_score >= 70 THEN 'HIGH' WHEN risk_score >= 40 THEN 'MEDIUM' "
        "ELSE 'LOW' END band, COUNT(*) c FROM inspection_results GROUP BY band"
    )

    a1, a2, a3 = st.columns(3)
    with a1:
        if fatigue_rows:
            df_f = pd.DataFrame([dict(r) for r in fatigue_rows])
            fig = px.pie(df_f, names="status", values="c", title="Driver Status Distribution",
                         color="status",
                         color_discrete_map={"SAFE": "#2ecc71", "WARNING": "#f5b942",
                                              "DROWSY": "#ff4d4f", "UNKNOWN": "#3fa9f5"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf5")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No RailVision data yet.")
    with a2:
        if tamper_rows:
            df_t = pd.DataFrame([dict(r) for r in tamper_rows])
            fig = px.pie(df_t, names="severity", values="c", title="Tamper Severity Distribution",
                         color="severity",
                         color_discrete_map={"HIGH": "#ff4d4f", "MEDIUM": "#f5b942", "LOW": "#2ecc71"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf5")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No SmartSeal data yet.")
    with a3:
        if risk_rows:
            df_r = pd.DataFrame([dict(r) for r in risk_rows])
            fig = px.pie(df_r, names="band", values="c", title="Track Risk Distribution",
                         color="band",
                         color_discrete_map={"HIGH": "#ff4d4f", "MEDIUM": "#f5b942", "LOW": "#2ecc71"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf5")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No TrackSentinel data yet.")
