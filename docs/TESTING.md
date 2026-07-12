# Testing Guide — RailwayBrain AI

This MVP is validated two ways: **headless automated checks** (no browser
needed) and a **manual walkthrough script** (for judges/demo purposes).

## 1. Automated headless checks

Streamlit ships a test harness (`streamlit.testing.v1.AppTest`) that runs the
full app script without a browser and surfaces any exception. Run:

```bash
pip install -r requirements.txt
python - <<'PY'
from streamlit.testing.v1 import AppTest

for page in ["Dashboard", "RailVision AI", "TrackSentinel AI",
             "SmartSeal AI", "Reports", "Settings", "About"]:
    at = AppTest.from_file("app.py")
    at.run(timeout=60)
    at.radio[0].set_value(page).run(timeout=60)
    assert not at.exception, f"{page} raised: {at.exception}"
    print(f"{page}: OK")
PY
```

Expected output: `OK` for all 7 pages, no exceptions.

## 2. Backend unit-level sanity checks

```bash
python - <<'PY'
from backend.database.db_manager import init_db, fetch_all
from backend.database.seed_data import seed_all
init_db(); seed_all()

from backend.railvision.fatigue_engine import FatigueEngine
FatigueEngine()  # raises if Haar cascades fail to load

from backend.tracksentinel.crack_growth_model import analyse_track
r = analyse_track("TEST-1", 10.0, "90UTS")
assert 0 <= r.risk_score <= 100

from backend.smartseal.tamper_simulator import simulate_tamper
w = fetch_all("SELECT wagon_id FROM wagons LIMIT 1")[0]["wagon_id"]
event = simulate_tamper(w)
assert event["severity"] in ("LOW", "MEDIUM", "HIGH")

print("All backend modules OK")
PY
```

## 3. Manual walkthrough (for live demo / judges)

1. **Dashboard** — confirm KPI cards populate (Today's Alerts, Active Drivers,
   Protected Wagons, High-Risk Tracks) and CPU/Memory gauges move on refresh.
2. **RailVision AI** → *Image Upload* — upload any photo with a visible face.
   Confirm a face/eye box is drawn and a fatigue score + status pill appear.
   Click "Save this event to database" and check it appears in *Event History*.
3. **TrackSentinel AI** → *Analyse Single Track* — pick a track, click
   "Generate & Analyse", confirm the crack-growth chart and risk score render.
   Try *Upload USFD CSV* with the downloadable sample template.
4. **SmartSeal AI** — confirm the live map shows wagon markers. Select a
   wagon, click **SIMULATE TAMPER**, confirm a red alert + RPF recommendation
   appears and the event shows in the timeline below.
5. **Reports** — select any dataset, download CSV, then click
   "Generate PDF Report" and download the PDF. Open it to confirm formatting.
6. **Settings** — confirm table row counts match what you've generated in the
   session; test "Clear ALL event data" and confirm tables empty out.
7. **About** — confirm the real-vs-simulated capability table is present and
   accurate to what you just tested above.

## 4. What "passing" means for this MVP

Because several data sources (USFD history, GPS, tamper sensors) are
explicitly simulated per the project brief, "passing" here means:
- No unhandled exceptions on any page or button.
- Every score/chart/recommendation is computed live from real input
  (uploaded image/video/CSV) wherever such input is provided — never hardcoded.
- Simulated components are clearly labelled with the orange "SIMULATED" badge.
