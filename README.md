# MindSense - Student Mental Health Analyzer

Flask + PostgreSQL application for student mental wellness screening with quick/full assessments, mood logs, analytics dashboards, and AI-generated summaries.

## Current production behavior

- Authentication: register, login, logout
- Quick assessment: severity-oriented quick check-in flow
- Full assessment: 10-question severity-aligned flow
- Mood logging: one log per day (strict mode)
- Dashboards: History + Analytics (charts, trends, paginated tables)
- AI features: analytics summary + assistant chat (Groq)

## Runtime architecture

- Backend: `app.py` + `db_helpers.py`
- Database: PostgreSQL (`DATABASE_URL` required)
- Models loaded at runtime:
    - `models/quick_model.pkl` + `models/quick_preprocessor.pkl`
    - `models/severity_model.pkl` + `models/severity_preprocessor.pkl`
- Frontend: server-rendered Jinja templates in `templates/`

## Required environment variables

- `DATABASE_URL` (required)
- `FLASK_SECRET` (required in production)
- `GROQ_API_KEY` (required for AI summary/chat)
- `GROQ_MODEL` (optional, default: `llama-3.1-8b-instant`)

## Local run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/mental_health_dev"
$env:FLASK_SECRET="replace-with-random-secret"
$env:GROQ_API_KEY="replace-with-groq-key"

python app.py
```

Open http://127.0.0.1:5000

## Pre-deploy cleanup checklist

1. Remove transient files: `__pycache__/`, `scripts/__pycache__/`.
2. Ensure local secrets are not committed (`.env.local` stays local only).
3. Confirm only required model artifacts exist in `models/` and are up to date.
4. Verify quick/full form fields match save logic (`templates/test.html` vs `app.py`).
5. Run a final smoke test locally: register/login, quick test, full test, history, analytics.

## Additional step before deploying this version

Run DB schema initialization/migration once against the target Render database so all additive columns exist:

```powershell
python -c "from db_helpers import init_db; print('init_db:', init_db())"
```

This is required before first traffic if your Render DB was created from an older schema.

## Deploy on Render

Use `render.yaml` (Blueprint) or set manually:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`

Set env vars in Render:

- `FLASK_SECRET`
- `GROQ_API_KEY`
- `GROQ_MODEL` (optional)

`DATABASE_URL` is provided automatically when using the database defined in `render.yaml`.

## Post-deploy smoke test

1. Open app root and login/register
2. Submit one quick assessment and one full assessment
3. Verify History and Analytics charts/tables load
4. Verify AI Summary loads and Refresh Summary works

## Notes on datasets and scripts

- Bundled training datasets were removed from this deployment branch to keep the repo lightweight.
- Legacy lifestyle-model scripts and dataset-generation scripts were removed.
- Runtime does not require `data/` contents; deployment uses prebuilt artifacts under `models/`.
- Current retained scripts (if present) are optional maintenance utilities, not required for serving.

## Disclaimer

This project is a wellness screening tool and not a medical diagnosis system.
