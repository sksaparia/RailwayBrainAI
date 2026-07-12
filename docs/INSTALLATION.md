# Installation Guide — RailwayBrain AI

## Prerequisites

- Python 3.10 or newer
- pip
- ~500 MB free disk space (for dependencies + SQLite DB + screenshots)
- No GPU required. No internet connection required after install (fully offline demo).

## Option A — One-command start (Linux/macOS)

```bash
git clone <your-repo-url>
cd RailwayBrainAI
./start.sh
```

This creates a virtual environment, installs everything in `requirements.txt`,
and launches the app. Streamlit will print a **Local URL** — open it in your browser.

## Option B — Manual setup (any OS, including Windows)

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd RailwayBrainAI

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501` by default.

## First Run

On first launch, RailwayBrain AI automatically:
1. Creates `backend/database/railwaybrain.db` (SQLite) if it doesn't exist.
2. Seeds it with simulated demo data (12 drivers, 20 track segments, 15 wagons).

No manual database setup is required.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: cv2` | Run `pip install -r requirements.txt` again inside the activated venv. |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` |
| Map tab (SmartSeal AI) shows blank | Ensure `folium` and `streamlit-folium` installed correctly; check terminal for errors. |
| Video upload fails to analyse | Confirm the file is a standard mp4/avi/mov; very large files may take longer — this is CPU-only OpenCV processing. |

## Resetting demo data

Open the **Settings** page inside the app → "Clear ALL event data" button, or
delete `backend/database/railwaybrain.db` and restart the app to regenerate
everything from scratch.
