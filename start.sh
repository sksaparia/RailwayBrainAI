#!/usr/bin/env bash
# RailwayBrain AI - Startup Script
# Creates a virtual environment (if missing), installs dependencies,
# and launches the Streamlit app.

set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Starting RailwayBrain AI..."
echo "Once running, open the Local URL shown below in your browser."
echo ""

streamlit run app.py
