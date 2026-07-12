# Deployment Guide — RailwayBrain AI

This MVP is designed to be deployable at **zero cost** for demo/pilot
purposes, then upgraded to production infrastructure as pilots convert to
paid contracts.

## Option 1 — Streamlit Community Cloud (recommended for judges, free)

1. Push this repository to a public (or private, invite-only) GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. "New app" → select the repo → main file path: `app.py`.
4. Deploy. Streamlit Cloud installs `requirements.txt` automatically.
5. You get a public URL (`https://<app-name>.streamlit.app`) shareable with
   Railway officers, Adani mentors, or Vande Bharatam judges — no install needed.

**Note:** Streamlit Cloud's filesystem is ephemeral — the SQLite DB resets on
redeploy/restart. This is fine for a live demo; for a persistent pilot,
migrate to Option 2 or 3 below.

## Option 2 — Self-hosted VM (DigitalOcean / AWS EC2 / Railway divisional server)

```bash
# On the VM:
sudo apt update && sudo apt install -y python3-venv python3-pip
git clone <your-repo-url> && cd RailwayBrainAI
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run persistently with systemd (recommended) or a process manager like tmux/screen:
streamlit run app.py --server.port 80 --server.headless true
```

For production, put Streamlit behind Nginx as a reverse proxy with TLS
(Let's Encrypt / Certbot), and persist `backend/database/railwaybrain.db` on
a mounted volume with regular backups.

## Option 3 — Docker (portable, works on any cloud or on-prem Railway server)

Create a `Dockerfile` (not bundled by default, add if containerising):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t railwaybrain-ai .
docker run -p 8501:8501 -v $(pwd)/backend/database:/app/backend/database railwaybrain-ai
```

The volume mount keeps the SQLite database persistent across container restarts.

## Migrating from SQLite to a production database

For a multi-division pilot with concurrent RPF/engineering users, replace
SQLite with PostgreSQL:
1. Swap `sqlite3` connections in `backend/database/db_manager.py` for
   `psycopg2`/`SQLAlchemy` with a Postgres connection string.
2. Table schema (see `SCHEMA` in `db_manager.py`) is standard SQL and
   migrates with minimal changes (mainly `AUTOINCREMENT` → `SERIAL`).
3. Point `DB_PATH`-style config at your managed Postgres instance
   (e.g., AWS RDS, DigitalOcean Managed Databases).

## Security notes before any real pilot deployment

- This demo has **no authentication** — add a login layer
  (`streamlit-authenticator` or a reverse-proxy SSO) before exposing to
  real Railway staff.
- Do not put real Railway operational data into this SQLite demo build
  without a security review — it is intentionally a local/offline demo.
- Screenshots and uploaded videos are stored unencrypted on local disk
  (`screenshots/railvision/`) — encrypt at rest before any real pilot.
