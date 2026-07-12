"""RailwayBrain AI - About page."""

from __future__ import annotations

import streamlit as st

from frontend.ui_helpers import section_title


def render() -> None:
    section_title("About RailwayBrain AI")

    st.markdown(
        """
RailwayBrain AI is a unified AI platform concept for Indian Railways, built as a
working software MVP to demonstrate technical feasibility for the
**Vande Bharatam Innovation Challenge (Adani Group)**.

It brings together three ideas already submitted to, and marked *In Process* by,
the Indian Railways Innovation Portal, into one working demonstration:

| Module | Purpose | Proposal ID | Challenge |
|---|---|---|---|
| RailVision AI | Driver fatigue detection | IC0000000170 | \u2014 |
| TrackSentinel AI | Rail defect growth prediction | IS0000000165 | IC0000000177 |
| SmartSeal AI | Freight consignment security | IS0000000163 | IC0000000293 |
        """
    )

    st.markdown('<div class="rb-section-title">What Is Real, and What Is Simulated</div>',
                unsafe_allow_html=True)
    st.markdown(
        "This build is honest about where it stands today. Every score, chart, and "
        "recommendation you see is **computed live** from whatever image, video, or "
        "CSV you provide \u2014 nothing is pre-baked. Where a real Railway hardware or "
        "data feed isn't available yet, the app clearly marks that data as simulated "
        "instead of pretending otherwise."
    )
    st.markdown(
        """
| Capability | This Demo | Full Hardware Deployment |
|---|---|---|
| Face / eye detection | **Real** \u2014 OpenCV runs live on your uploaded image or video | Upgraded to YOLOv9 + dual 4K/IR cameras on an NVIDIA Jetson Orin NX |
| Fatigue scoring | **Real** \u2014 computed from the actual detection result | Same scoring logic, calibrated on a real driver dataset over time |
| Crack growth prediction | **Real** \u2014 Paris Law physics model computed live on the input | Same model, calibrated with RDSO data and machine learning |
| USFD inspection history | Simulated, unless you upload your own CSV | Ingested directly from Railway's USFD trolleys / digitised records |
| Wagon GPS position | Simulated movement along a corridor | Real GPS via LTE-M/NB-IoT e-Seal hardware |
| Tamper sensor events | Simulated (triggered on demand, mapped to the 6 real sensor types) | Real magnetic, cable, accelerometer, light, replacement and jam sensors |
| RPF / maintenance recommendations | **Real** \u2014 generated live from the actual detection or risk output | Same recommendation logic, feeding a real RPF dispatch system |

In short: the **decision logic is real**; only the **source of the input data**
changes between this demo and a hardware-connected deployment.
        """
    )

    st.markdown('<div class="rb-section-title">Benefits</div>', unsafe_allow_html=True)
    st.markdown(
        """
- **Safety** \u2014 earlier warning of driver fatigue and rail defects reduces the
  chance of accidents caused by human or infrastructure failure.
- **Cost avoidance** \u2014 catching a track defect while it is still small is far
  cheaper than an emergency repair or, worse, a derailment.
- **Freight security** \u2014 tamper alerts reach the right team within minutes
  instead of being discovered at the destination.
- **One platform, three problems** \u2014 a single dashboard for divisional staff,
  instead of three disconnected tools.
- **Zero-cost to pilot** \u2014 built entirely on free and open-source software, so a
  trial deployment carries no licensing cost.
        """
    )

    st.markdown('<div class="rb-section-title">Roadmap</div>', unsafe_allow_html=True)
    st.markdown(
        """
- **Phase 1 (Year 1\u20132):** RailVision AI, TrackSentinel AI, SmartSeal AI \u2014 pilot stage (this build).
- **Phase 2 (Year 3\u20134):** Predictive Maintenance, Revenue Intelligence, Energy Intelligence,
  Staff Intelligence, Procurement Intelligence.
- **Phase 3 (Year 5+):** A unified knowledge graph connecting all of Railways' major IT systems.
        """
    )

    st.markdown('<div class="rb-section-title">Future Scope</div>', unsafe_allow_html=True)
    st.markdown(
        """
- Replace the simulated GPS/tamper feed with real LTE-M/NB-IoT e-Seal hardware.
- Replace the Haar-cascade fatigue pipeline with the full YOLOv9 + thermal camera stack.
- Connect TrackSentinel AI to Railway's digitised USFD records via the CRIS API.
- Add the Phase 2 modules once Phase 1 pilot data validates the approach.
        """
    )

    st.markdown('<div class="rb-section-title">Founder</div>', unsafe_allow_html=True)
    st.markdown(
        """
**Sachin Saparia** \u2014 Jamshedpur, Jharkhand.
B.Com | GST & Tally Professional | Individual Innovator.

No engineering degree, no prior professional coding background. Designed the
RailwayBrain AI architecture and all three underlying proposals using domain
knowledge of railway operations and freight economics \u2014 then built this
working software demonstration to show the architecture holds up as real,
running code, not just a paper proposal.
        """
    )

    st.caption("Contact: sachinsaparia123@gmail.com")
